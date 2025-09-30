import os
import re
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# Try to import required packages
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("Warning: Google Generative AI package not installed. Some features will be limited.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not installed. Image input will not be available.")
    print("Install with: pip install pillow")

try:
    import pytesseract
    import pdf2image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: pytesseract or pdf2image not installed. Attempting to install them now...")
    try:
        import subprocess
        print("Installing pdf2image and pytesseract packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pdf2image", "pytesseract"])
        print("Packages installed successfully! Importing them now...")
        import pytesseract
        import pdf2image
        OCR_AVAILABLE = True
        print("PDF processing packages successfully installed and imported.")
    except Exception as e:
        print(f"Error installing packages: {e}")
        print("Please install manually with: pip install pytesseract pdf2image")
        print("Note: For pytesseract to work, you also need to install Tesseract OCR engine:")
        print("- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        print("- Mac: brew install tesseract")
        print("- Linux: apt-get install tesseract-ocr")

# =========================
# CONFIG: PASTE YOUR API KEY HERE
# =========================
API_KEY = "my_api_key"  # <-- Replace with your Gemini API key

# =========================
# IMAGE OCR FUNCTIONS
# =========================
def maybe_resize_image(pil_img, max_side=1600):
    """Resize image if too large."""
    w, h = pil_img.size
    if max(w, h) <= max_side:
        return pil_img
    scale = max_side / max(w, h)
    new_size = (int(w * scale), int(h * scale))
    return pil_img.resize(new_size, Image.LANCZOS)

def extract_text_from_image(image_path):
    """Extract text from image using Gemini OCR or pytesseract."""
    if not Path(image_path).exists():
        print(f"Error: File not found: {image_path}")
        return None
    
    file_ext = Path(image_path).suffix.lower()
    
    try:
        # Handle PDF files
        if file_ext == '.pdf':
            if not OCR_AVAILABLE:
                print("Error: pdf2image and pytesseract are required for PDF processing.")
                return None
            
            print("Converting PDF to images...")
            pages = pdf2image.convert_from_path(image_path)
            text_content = ""
            
            for i, page in enumerate(pages):
                print(f"Processing page {i+1}/{len(pages)}...")
                text_content += pytesseract.image_to_string(page) + "\n\n"
            
            return text_content.strip()
        
        # Handle image files
        pil_img = Image.open(image_path).convert("RGB")
        pil_img = maybe_resize_image(pil_img)
        
        # Try Gemini first (better quality)
        if PIL_AVAILABLE and GENAI_AVAILABLE:
            try:
                client = genai.Client(api_key=API_KEY)
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=[
                        "Extract all text from this image. Preserve the structure, sections, and formatting. If there are sections like 'Aim', 'Algorithm', 'Program', 'Output', and 'Result', make sure to clearly identify them.",
                        pil_img,
                    ],
                )
                
                return response.text.strip() if hasattr(response, "text") else str(response)
            except Exception as e:
                print(f"Gemini OCR failed: {e}. Falling back to pytesseract...")
        
        # Fallback to pytesseract
        if OCR_AVAILABLE:
            return pytesseract.image_to_string(pil_img)
        else:
            print("Error: No OCR method available. Install pytesseract or enable Gemini API.")
            return None
            
    except Exception as e:
        print(f"Error extracting text from file: {e}")
        return None

# =========================
# FILE UPLOAD FUNCTION
# =========================
def select_image_file():
    """Open file dialog to select an image file or PDF."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)  # Bring dialog to front
    
    file_path = filedialog.askopenfilename(
        title="Select Image File or PDF with Student Submission",
        filetypes=[
            ("All supported files", "*.jpg *.jpeg *.png *.pdf"),
            ("Image files", "*.jpg *.jpeg *.png"),
            ("PDF files", "*.pdf"),
            ("All files", ".")
        ]
    )
    
    root.destroy()
    return file_path

# =========================
# SUBMISSION PARSING FUNCTIONS
# =========================
def parse_submission_sections(text_content):
    """
    Parse the extracted text into Aim, Algorithm, Program, Output and Result sections.
    """
    sections = {
        "aim": "",
        "algorithm": "",
        "program": "",
        "output": "",
        "result": ""
    }
    
    # Try to find sections using regex patterns
    patterns = {
        "aim": r"(?:^|\n)(?:AIM|Aim|aim|OBJECTIVE|Objective)(?::|\.|\s*\n)(.?)(?=(?:\n\s(?:ALGORITHM|Algorithm|algorithm|PROCEDURE|Procedure|PROGRAM|Program|program|OUTPUT|Output|output|RESULT|Result|result)(?::|\.|\s*\n))|$)",
        "algorithm": r"(?:^|\n)(?:ALGORITHM|Algorithm|algorithm|PROCEDURE|Procedure)(?::|\.|\s*\n)(.?)(?=(?:\n\s(?:PROGRAM|Program|program|OUTPUT|Output|output|RESULT|Result|result)(?::|\.|\s*\n))|$)",
        "program": r"(?:^|\n)(?:PROGRAM|Program|program|CODE|Code|code|SOURCE CODE|Source Code)(?::|\.|\s*\n)(.?)(?=(?:\n\s(?:OUTPUT|Output|output|RESULT|Result|result)(?::|\.|\s*\n))|$)",
        "output": r"(?:^|\n)(?:OUTPUT|Output|output|EXECUTION|Execution|execution)(?::|\.|\s*\n)(.?)(?=(?:\n\s(?:RESULT|Result|result|CONCLUSION|Conclusion|conclusion)(?::|\.|\s*\n))|$)",
        "result": r"(?:^|\n)(?:RESULT|Result|result|CONCLUSION|Conclusion|conclusion)(?::|\.|\s*\n)(.*?)(?=$)"
    }
    
    for section, pattern in patterns.items():
        matches = re.search(pattern, text_content, re.DOTALL | re.IGNORECASE)
        if matches:
            sections[section] = matches.group(1).strip()
    
    # If sections weren't found with regex, try to use Gemini to extract them
    if GENAI_AVAILABLE and (not sections["aim"] or not sections["algorithm"] or not sections["program"]):
        try:
            client = genai.Client(api_key=API_KEY)
            prompt = f"""
            Extract the following sections from this student submission:
            - Aim/Objective
            - Algorithm/Procedure
            - Program/Code
            - Output/Execution
            - Result/Conclusion
            
            Format your response as:
            
            AIM:
            [extracted aim]
            
            ALGORITHM:
            [extracted algorithm]
            
            PROGRAM:
            [extracted program]
            
            OUTPUT:
            [extracted output]
            
            RESULT:
            [extracted result]
            
            Here is the submission text:
            {text_content}
            """
            
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp", contents=prompt
            )
            
            if hasattr(response, 'text'):
                # Parse the response to extract sections
                ai_sections = response.text
                for section in sections.keys():
                    section_pattern = rf"{section.upper()}:\s*\n(.*?)(?=\n\w+:|$)"
                    section_match = re.search(section_pattern, ai_sections, re.DOTALL | re.IGNORECASE)
                    if section_match and not sections[section]:
                        sections[section] = section_match.group(1).strip()
        except Exception as e:
            print(f"Error using Gemini to parse sections: {e}")
    
    return sections

# =========================
# STEP 1: CODE INPUT (TEXT OR IMAGE)
# =========================
def get_code_from_user():
    """
    Get code input from user - either typed/pasted or from an uploaded image file.
    """
    print("\n" + "="*50)
    print("CODE INPUT OPTIONS:")
    print("1. Type/paste code directly")
    print("2. Upload image file (JPG/PNG) - File dialog will open")
    print("="*50)
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "2":
        # Image input with file dialog
        if not PIL_AVAILABLE or not GENAI_AVAILABLE:
            print("Error: Image input requires PIL and google-generativeai packages.")
            print("Falling back to text input...")
            choice = "1"
        else:
            print("\nOpening file dialog...")
            print("(If dialog doesn't appear, check behind other windows)")
            image_path = select_image_file()
            
            if image_path:
                print(f"Selected file: {os.path.basename(image_path)}")
                print("Extracting code from image...")
                code = extract_text_from_image(image_path)
                if code:
                    print("\n=== Extracted Code ===")
                    print(code)
                    print("="*50)
                    confirm = input("\nUse this extracted code? (y/n): ").strip().lower()
                    if confirm == 'y':
                        return code
                    else:
                        print("Falling back to text input...")
                        choice = "1"
                else:
                    print("Failed to extract code from image. Falling back to text input...")
                    choice = "1"
            else:
                print("No file selected. Falling back to text input...")
                choice = "1"
    
    # Text input (default)
    if choice == "1" or choice != "2":
        print("\nEnter/paste your code below. Type 'END' in a new line when finished:")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        return "\n".join(lines)

# =========================
# STEP 1b: MAX MARKS INPUT WITH VALIDATION
# =========================
def get_max_marks():
    while True:
        try:
            marks = float(input("\nEnter the maximum marks for this question: "))
            if marks <= 0:
                print("Marks must be positive!")
                continue
            return marks
        except ValueError:
            print("Invalid input! Please enter a numeric value for marks.")

# =========================
# STEP 2: PROBLEM PARSING
# =========================
def parse_problem_with_gemini(problem_text):
    """
    Use Gemini to parse problem requirements and identify expected solution patterns.
    """
    if not GENAI_AVAILABLE:
        print("Google Generative AI package not installed. Using offline mode.")
        return offline_parse_problem(problem_text), []
    
    try:
        client = genai.Client(api_key=API_KEY)
        prompt = f"""
        Analyze the problem statement and extract:
        1. Required function name
        2. Input parameters and their types
        3. Expected output type and format
        4. Edge cases to consider
        5. Key algorithmic concepts needed (loops, conditions, recursion, etc.)
        6. Common mistakes students might make
        
        Problem: {problem_text}
        
        Format the response clearly with sections.
        """
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp", contents=prompt
        )
        
        # Extract common mistakes
        mistakes_prompt = f"""
        Based on this problem, list the 5-7 most common mistakes students make when solving it.
        Be specific about coding errors, logic errors, and edge case handling.
        
        Problem: {problem_text}
        
        Format as a numbered list.
        """
        mistakes_response = client.models.generate_content(
            model="gemini-2.0-flash-exp", contents=mistakes_prompt
        )
        
        common_mistakes = mistakes_response.text if hasattr(mistakes_response, 'text') else ""
        
        return response.text, common_mistakes
    except Exception as e:
        print(f"API Error: {str(e)}")
        print("Falling back to offline mode...")
        return offline_parse_problem(problem_text), []

def offline_parse_problem(problem_text):
    """
    Basic offline parsing of problem requirements.
    """
    function_match = re.search(r'function\s+(\w+)|def\s+(\w+)', problem_text, re.IGNORECASE)
    function_name = "Unknown"
    if function_match:
        function_name = function_match.group(1) or function_match.group(2)
    
    return f"""
    Problem Analysis:
    
    1. Required function name: {function_name}
    2. Input parameters: Based on problem description
    3. Expected output: Based on problem requirements
    4. Edge cases: Empty input, invalid input, boundary conditions
    5. Key concepts: Based on problem complexity
    """

# =========================
# STEP 3: CODE VALIDATION
# =========================
def validate_code(code):
    """
    Check for syntax errors and basic code issues.
    Returns (error_message, mistake_points)
    """
    mistake_points = []
    
    # Check for syntax errors
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        mistake_points.append(f"• Syntax Error at line {e.lineno}: {e.msg}")
        return f"Syntax Error: {str(e)}", mistake_points
    except IndentationError as e:
        mistake_points.append(f"• Indentation Error: {e.msg}")
        return f"Indentation Error: {str(e)}", mistake_points
    except Exception as e:
        mistake_points.append(f"• Compilation Error: {str(e)}")
        return f"Compilation Error: {str(e)}", mistake_points
    
    # Basic code quality checks
    lines = code.split('\n')
    
    # Check for common issues
    if not any('def ' in line for line in lines):
        mistake_points.append("• No function definition found")
    
    if 'return' not in code and 'print' not in code:
        mistake_points.append("• No return statement or print output found")
    
    # Check for empty except blocks
    if 'except:' in code and 'pass' in code:
        mistake_points.append("• Empty except block found (poor error handling)")
    
    # Check for hardcoded values when input is expected
    if 'input(' not in code and not any('def ' in line for line in lines):
        if any(char.isdigit() for char in code):
            mistake_points.append("• Possible hardcoded values instead of parameters")
    
    # Check for infinite loops
    if 'while True:' in code and 'break' not in code:
        mistake_points.append("• Potential infinite loop detected")
    
    # Check for unused variables (simple check)
    import_lines = [l for l in lines if l.strip().startswith('import')]
    if import_lines:
        for imp in import_lines:
            module = imp.split()[1].split('.')[0]
            if module not in code.replace(imp, ''):
                mistake_points.append(f"• Unused import: {module}")
    
    if mistake_points:
        return "Code has issues (see mistake points)", mistake_points
    
    return "No syntax errors found", []

# =========================
# STEP 4: SUBMISSION EVALUATION WITH MARKING SCHEME
# =========================
def evaluate_submission_with_marking_scheme(sections, problem_text):
    """
    Evaluate student submission with the specified marking scheme:
    Aim=10, Algorithm=15, Program=50, Output=15, Result=10
    """
    if not GENAI_AVAILABLE:
        print("Google Generative AI package not installed. Using offline mode.")
        return offline_evaluate_submission(sections, problem_text)
    
    try:
        client = genai.Client(api_key=API_KEY)
        
        # First evaluate if Aim, Algorithm and Result are related to the question
        relevance_prompt = f"""
        Evaluate if the following sections are relevant to the given question.
        
        Question: {problem_text}
        
        AIM:
        {sections['aim']}
        
        ALGORITHM:
        {sections['algorithm']}
        
        RESULT:
        {sections['result']}
        
        For each section, provide:
        1. A score out of 10 for relevance to the question
        2. Brief explanation for the score
        3. Whether the section is directly related to the question (yes/no)
        
        Format your response as:
        
        AIM EVALUATION:
        Score: [0-10]
        Explanation: [brief explanation]
        Related: [yes/no]
        
        ALGORITHM EVALUATION:
        Score: [0-10]
        Explanation: [brief explanation]
        Related: [yes/no]
        
        RESULT EVALUATION:
        Score: [0-10]
        Explanation: [brief explanation]
        Related: [yes/no]
        """
        
        relevance_response = client.models.generate_content(
            model="gemini-2.0-flash-exp", contents=relevance_prompt
        )
        
        relevance_text = relevance_response.text if hasattr(relevance_response, 'text') else ""
        
        # Now evaluate the Program and Output sections in detail
        program_prompt = f"""
        Evaluate the following program code against the given question.
        
        Question: {problem_text}
        
        Program Code:
        {sections['program']}
        
        Output:
        {sections['output']}
        
        Provide a detailed evaluation with these specific scores:
        
        1. CORRECTNESS (0-10): Does the code solve the problem correctly?
           - Does it produce the expected output?
           - Are all requirements met?
           - Does it handle inputs correctly?
        
        2. EFFICIENCY (0-10): How efficient is the solution?
           - Is the algorithm efficient?
           - Is the approach logical and well-reasoned?
           - Are edge cases handled properly?
        
        3. CODE QUALITY (0-10): How well is the code written?
           - Is the code well-organized?
           - Are variable names meaningful?
           - Is there proper indentation and formatting?
           - Are there comments where needed?
        
        4. OUTPUT CORRECTNESS (0-10): Is the output correct?
           - Does it match expected results?
           - Is it formatted properly?
           - Is it complete?
        
        5. OUTPUT PRESENTATION (0-10): How well is the output presented?
           - Is it clear and readable?
           - Does it provide necessary information?
           - Is it well-formatted?
        
        Also provide:
        - List of specific mistakes or issues found
        - Brief summary of strengths and weaknesses
        
        Format your response with clear sections and numeric scores.
        """
        
        program_response = client.models.generate_content(
            model="gemini-2.0-flash-exp", contents=program_prompt
        )
        
        program_text = program_response.text if hasattr(program_response, 'text') else ""
        
        # Calculate scores based on the marking scheme
        scores = parse_submission_scores(relevance_text, program_text)
        
        # Combine evaluation texts
        evaluation_text = f"""
        SUBMISSION EVALUATION
        
        {relevance_text}
        
        {program_text}
        """
        
        return evaluation_text, scores
    except Exception as e:
        print(f"API Error: {str(e)}")
        print("Falling back to offline mode...")
        return offline_evaluate_submission(sections, problem_text)

def parse_submission_scores(relevance_text, program_text):
    """
    Parse scores from evaluation texts and calculate final scores based on marking scheme:
    Aim=10, Algorithm=15, Program=50, Output=15, Result=10
    """
    scores = {
        "aim": {"max": 10, "score": 0, "explanation": ""},
        "algorithm": {"max": 15, "score": 0, "explanation": ""},
        "program": {"max": 50, "score": 0, "explanation": ""},
        "output": {"max": 15, "score": 0, "explanation": ""},
        "result": {"max": 10, "score": 0, "explanation": ""},
        "total": {"max": 100, "score": 0}
    }
    
    # Parse Aim score (out of 10)
    aim_match = re.search(r"AIM EVALUATION:.?Score:\s(\d+(?:\.\d+)?)", relevance_text, re.DOTALL)
    if aim_match:
        aim_score = float(aim_match.group(1))
        scores["aim"]["score"] = aim_score
        
        # Extract explanation
        aim_exp_match = re.search(r"AIM EVALUATION:.?Explanation:\s(.*?)(?=Related:|$)", relevance_text, re.DOTALL)
        if aim_exp_match:
            scores["aim"]["explanation"] = aim_exp_match.group(1).strip()
    
    # Parse Algorithm score (out of 10, scale to 15)
    algo_match = re.search(r"ALGORITHM EVALUATION:.?Score:\s(\d+(?:\.\d+)?)", relevance_text, re.DOTALL)
    if algo_match:
        algo_score = float(algo_match.group(1))
        scores["algorithm"]["score"] = (algo_score / 10) * 15
        
        # Extract explanation
        algo_exp_match = re.search(r"ALGORITHM EVALUATION:.?Explanation:\s(.*?)(?=Related:|$)", relevance_text, re.DOTALL)
        if algo_exp_match:
            scores["algorithm"]["explanation"] = algo_exp_match.group(1).strip()
    
    # Parse Result score (out of 10)
    result_match = re.search(r"RESULT EVALUATION:.?Score:\s(\d+(?:\.\d+)?)", relevance_text, re.DOTALL)
    if result_match:
        result_score = float(result_match.group(1))
        scores["result"]["score"] = result_score
        
        # Extract explanation
        result_exp_match = re.search(r"RESULT EVALUATION:.?Explanation:\s(.*?)(?=Related:|$)", relevance_text, re.DOTALL)
        if result_exp_match:
            scores["result"]["explanation"] = result_exp_match.group(1).strip()
    
    # Parse Program score (combine correctness, efficiency, code quality - scale to 50)
    correctness_match = re.search(r"CORRECTNESS.*?(\d+(?:\.\d+)?)/10", program_text, re.DOTALL)
    efficiency_match = re.search(r"EFFICIENCY.*?(\d+(?:\.\d+)?)/10", program_text, re.DOTALL)
    quality_match = re.search(r"CODE QUALITY.*?(\d+(?:\.\d+)?)/10", program_text, re.DOTALL)
    
    correctness = float(correctness_match.group(1)) if correctness_match else 5
    efficiency = float(efficiency_match.group(1)) if efficiency_match else 5
    quality = float(quality_match.group(1)) if quality_match else 5
    
    # Program score is weighted average of correctness (50%), efficiency (30%), quality (20%)
    program_score = (correctness * 0.5 + efficiency * 0.3 + quality * 0.2) * 5  # Scale to 50
    scores["program"]["score"] = program_score
    
    # Extract program explanation
    strengths_match = re.search(r"strengths.?:(.?)(?=weaknesses|$)", program_text, re.DOTALL | re.IGNORECASE)
    if strengths_match:
        scores["program"]["explanation"] = strengths_match.group(1).strip()
    
    # Parse Output score (combine output correctness and presentation - scale to 15)
    output_corr_match = re.search(r"OUTPUT CORRECTNESS.*?(\d+(?:\.\d+)?)/10", program_text, re.DOTALL)
    output_pres_match = re.search(r"OUTPUT PRESENTATION.*?(\d+(?:\.\d+)?)/10", program_text, re.DOTALL)
    
    output_corr = float(output_corr_match.group(1)) if output_corr_match else 5
    output_pres = float(output_pres_match.group(1)) if output_pres_match else 5
    
    # Output score is weighted average of correctness (70%) and presentation (30%)
    output_score = (output_corr * 0.7 + output_pres * 0.3) * 1.5  # Scale to 15
    scores["output"]["score"] = output_score
    
    # Calculate total score
    total_score = (
        scores["aim"]["score"] +
        scores["algorithm"]["score"] +
        scores["program"]["score"] +
        scores["output"]["score"] +
        scores["result"]["score"]
    )
    
    # Ensure minimum 60% if submission is completely unrelated
    if total_score < 60:
        total_score = 60
    
    scores["total"]["score"] = round(total_score, 2)
    
    return scores

def offline_evaluate_submission(sections, problem_text):
    """
    Offline evaluation of submission with default scores.
    """
    scores = {
        "aim": {"max": 10, "score": 7, "explanation": "Basic aim provided but could be more specific."},
        "algorithm": {"max": 15, "score": 10, "explanation": "Algorithm covers main steps but lacks detail."},
        "program": {"max": 50, "score": 35, "explanation": "Program implements basic functionality."},
        "output": {"max": 15, "score": 10, "explanation": "Output shows expected results."},
        "result": {"max": 10, "score": 7, "explanation": "Result summarizes findings but lacks analysis."},
        "total": {"max": 100, "score": 69}
    }
    
    evaluation_text = f"""
    SUBMISSION EVALUATION (OFFLINE MODE)
    
    AIM EVALUATION:
    Score: 7/10
    Explanation: Basic aim provided but could be more specific.
    Related: Yes
    
    ALGORITHM EVALUATION:
    Score: 6.7/10
    Explanation: Algorithm covers main steps but lacks detail.
    Related: Yes
    
    PROGRAM EVALUATION:
    Correctness: 7/10
    Efficiency: 6/10
    Code Quality: 7/10
    
    OUTPUT EVALUATION:
    Correctness: 7/10
    Presentation: 6/10
    
    RESULT EVALUATION:
    Score: 7/10
    Explanation: Result summarizes findings but lacks analysis.
    Related: Yes
    
    Strengths: Basic implementation meets requirements.
    Weaknesses: Could improve efficiency and add more comments.
    """
    
    return evaluation_text, scores

def parse_mark_breakdown(evaluation_text):
    """
    Extract individual scores from evaluation text.
    """
    breakdown = {
        "problem_solving": 5,
        "logic_quality": 5,
        "readability": 5,
        "effort": 5,
        "overall": 5
    }
    
    # Try to extract scores using regex
    patterns = [
        (r"PROBLEM SOLVING.*?(\d+(?:\.\d+)?)/10", "problem_solving"),
        (r"LOGIC QUALITY.*?(\d+(?:\.\d+)?)/10", "logic_quality"),
        (r"READABILITY.*?(\d+(?:\.\d+)?)/10", "readability"),
        (r"EFFORT.*?(\d+(?:\.\d+)?)/10", "effort"),
        (r"Overall.?score.?(\d+(?:\.\d+)?)/10", "overall"),
        (r"weighted score.*?(\d+(?:\.\d+)?)/10", "overall")
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, evaluation_text, re.IGNORECASE | re.DOTALL)
        if match:
            breakdown[key] = float(match.group(1))
    
    # If overall not found, calculate average
    if breakdown["overall"] == 5:
        breakdown["overall"] = (breakdown["problem_solving"] + breakdown["logic_quality"] + 
                                breakdown["readability"] + breakdown["effort"]) / 4
    
    return breakdown

def offline_evaluate_code_with_breakdown(code, problem_text):
    """
    Offline evaluation with mark breakdown.
    """
    breakdown = {
        "problem_solving": 5,
        "logic_quality": 5,
        "readability": 5,
        "effort": 5,
        "overall": 5
    }
    
    try:
        compile(code, "<string>", "exec")
        syntax_ok = True
        breakdown["problem_solving"] = 6
    except:
        syntax_ok = False
        breakdown["problem_solving"] = 2
    
    # Check code features
    has_function = bool(re.search(r'def\s+\w+\s*\(', code))
    has_return = 'return' in code
    has_comments = '#' in code
    lines = code.split('\n')
    non_empty_lines = [l for l in lines if l.strip()]
    
    # Logic quality
    if syntax_ok and has_function:
        breakdown["logic_quality"] = 6
    elif syntax_ok:
        breakdown["logic_quality"] = 4
    else:
        breakdown["logic_quality"] = 2
    
    # Readability
    if has_comments and len(non_empty_lines) > 5:
        breakdown["readability"] = 7
    elif len(non_empty_lines) > 3:
        breakdown["readability"] = 5
    else:
        breakdown["readability"] = 3
    
    # Effort
    if len(non_empty_lines) > 10:
        breakdown["effort"] = 8
    elif len(non_empty_lines) > 5:
        breakdown["effort"] = 6
    else:
        breakdown["effort"] = 4
    
    # Overall
    breakdown["overall"] = sum([breakdown["problem_solving"], breakdown["logic_quality"],
                                breakdown["readability"], breakdown["effort"]]) / 4
    
    evaluation = f"""
    Code Evaluation:
    
    1. PROBLEM SOLVING: {breakdown['problem_solving']}/10
    2. LOGIC QUALITY: {breakdown['logic_quality']}/10
    3. READABILITY & STRUCTURE: {breakdown['readability']}/10
    4. EFFORT & RELEVANCE: {breakdown['effort']}/10
    
    Overall Score: {breakdown['overall']}/10
    """
    
    return evaluation, [], breakdown

def extract_mistakes_from_evaluation(evaluation_text):
    """
    Extract mistake points from the evaluation text.
    """
    mistakes = []
    lines = evaluation_text.split('\n')
    
    # Look for lines that indicate mistakes
    mistake_keywords = ['mistake', 'error', 'incorrect', 'wrong', 'missing', 'fails', 'doesn\'t handle']
    
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in mistake_keywords):
            # Clean and format the mistake
            cleaned = line.strip()
            if cleaned and not cleaned.startswith('#'):
                if not cleaned.startswith('•'):
                    cleaned = '• ' + cleaned
                mistakes.append(cleaned)
    
    # Also look for numbered mistakes
    for i, line in enumerate(lines):
        if re.match(r'^\d+\..*mistake|error|incorrect', line, re.IGNORECASE):
            mistakes.append('• ' + line.strip())
    
    return mistakes[:10]  # Limit to 10 mistakes

# =========================
# STEP 5: GRADING WITH BREAKDOWN
# =========================
def calculate_grade_with_breakdown(breakdown, max_marks, all_mistakes):
    """
    Calculate grade based on detailed breakdown.
    """
    # Weight for each component
    weights = {
        "problem_solving": 0.40,  # 40%
        "logic_quality": 0.30,    # 30%
        "readability": 0.15,       # 15%
        "effort": 0.15            # 15%
    }
    
    # Calculate weighted score
    weighted_score = 0
    for key, weight in weights.items():
        weighted_score += (breakdown[key] / 10) * weight
    
    # Convert to marks
    score = weighted_score * max_marks
    
    # Apply penalty for mistakes (less harsh)
    total_mistakes = len(all_mistakes)
    if total_mistakes > 0:
        # Each mistake reduces score by 3%, max reduction 20%
        penalty = min(0.2, total_mistakes * 0.03)
        score *= (1 - penalty)
    
    # Calculate individual component marks
    component_marks = {}
    for key, weight in weights.items():
        component_marks[key] = round((breakdown[key] / 10) * weight * max_marks, 2)
    
    return max(0, round(score, 2)), component_marks

# =========================
# MAIN INTERACTIVE FUNCTION
# =========================
def run_pipeline():
    print("\n" + "="*60)
    print(" STUDENT SUBMISSION EVALUATOR ")
    print(" Using Gemini API ")
    print("="*60)
    
    # Get problem statement
    print("\nSTEP 1: PROBLEM STATEMENT")
    print("-" * 40)
    problem_text = input("Enter the problem/question text: ").strip()
    if not problem_text:
        print("Error: Problem statement cannot be empty!")
        return
    
    # Get student submission (text or image/PDF upload)
    print("\nSTEP 2: STUDENT SUBMISSION INPUT")
    print("-" * 40)
    print("\n" + "="*50)
    print("SUBMISSION INPUT OPTIONS:")
    print("1. Type/paste submission directly")
    print("2. Upload image file (JPG/PNG) or PDF - File dialog will open")
    print("="*50)
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    submission_text = ""
    if choice == "2":
        # Image/PDF input with file dialog
        if not PIL_AVAILABLE:
            print("Error: Image input requires PIL package.")
            print("Falling back to text input...")
            choice = "1"
        else:
            print("\nOpening file dialog...")
            print("(If dialog doesn't appear, check behind other windows)")
            file_path = select_image_file()
            
            if file_path:
                print(f"Selected file: {os.path.basename(file_path)}")
                print("Extracting text from file...")
                submission_text = extract_text_from_image(file_path)
                if submission_text:
                    print("\n=== Extracted Text Preview ===")
                    preview = submission_text[:500] + "..." if len(submission_text) > 500 else submission_text
                    print(preview)
                    print("="*50)
                    confirm = input("\nUse this extracted text? (y/n): ").strip().lower()
                    if confirm != 'y':
                        print("Falling back to text input...")
                        choice = "1"
                else:
                    print("Failed to extract text from file. Falling back to text input...")
                    choice = "1"
            else:
                print("No file selected. Falling back to text input...")
                choice = "1"
    
    # Text input (default)
    if choice == "1" or choice != "2":
        print("\nEnter/paste your submission below. Type 'END' in a new line when finished:")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        submission_text = "\n".join(lines)
    
    if not submission_text or not submission_text.strip():
        print("Error: No submission provided!")
        return
    
    # Parse submission into sections
    print("\nSTEP 3: PARSING SUBMISSION INTO SECTIONS")
    print("-" * 40)
    sections = parse_submission_sections(submission_text)
    
    # Show parsed sections
    print("\nParsed Sections:")
    for section, content in sections.items():
        preview = content[:100] + "..." if len(content) > 100 else content
        print(f"\n{section.upper()}:")
        print(preview)
    
    # Evaluate submission with marking scheme
    print("\nSTEP 4: EVALUATING SUBMISSION")
    print("-" * 40)
    evaluation, scores = evaluate_submission_with_marking_scheme(sections, problem_text)
    
    # Display results
    print("\n" + "="*60)
    print(" EVALUATION RESULTS ")
    print("="*60)
    
    print("\n📋 DETAILED EVALUATION:")
    print("-" * 40)
    print(evaluation)
    
    print("\n📈 MARK BREAKDOWN:")
    print("-" * 40)
    print(f"1. Aim ({scores['aim']['max']}%):                {scores['aim']['score']:.2f}/{scores['aim']['max']}")
    print(f"   - {scores['aim']['explanation']}")
    print(f"2. Algorithm ({scores['algorithm']['max']}%):     {scores['algorithm']['score']:.2f}/{scores['algorithm']['max']}")
    print(f"   - {scores['algorithm']['explanation']}")
    print(f"3. Program ({scores['program']['max']}%):        {scores['program']['score']:.2f}/{scores['program']['max']}")
    print(f"   - {scores['program']['explanation']}")
    print(f"4. Output ({scores['output']['max']}%):         {scores['output']['score']:.2f}/{scores['output']['max']}")
    print(f"5. Result ({scores['result']['max']}%):         {scores['result']['score']:.2f}/{scores['result']['max']}")
    print(f"   - {scores['result']['explanation']}")
    
    print("\n✅ FINAL GRADE:")
    print("-" * 40)
    print(f"Total Score: {scores['total']['score']}/{scores['total']['max']}")
    # percentage = (scores['total']['score']/scores['total']['max']) * 100
    # print(f"Percentage: {percentage:.1f}%")
    
    # Generate markdown output
    markdown_output = generate_markdown_output(scores, evaluation, problem_text)
    print("\n📝 MARKDOWN OUTPUT GENERATED")
    print("-" * 40)
    print("A detailed markdown evaluation has been generated.")
    
    # Ask if user wants to save the markdown output
    save_option = input("\nDo you want to save the evaluation as a markdown file? (y/n): ").strip().lower()
    if save_option == 'y':
        save_path = input("Enter file path to save (or press Enter for default): ").strip()
        if not save_path:
            save_path = "evaluation_result.md"
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(markdown_output)
            print(f"Evaluation saved to {save_path}")
        except Exception as e:
            print(f"Error saving file: {e}")

def generate_markdown_output(scores, evaluation_text, problem_text):
    """Generate a formatted markdown output with the evaluation results."""
    markdown = f"""
# Student Submission Evaluation

## Problem Statement
{problem_text}

## Evaluation Summary

| Section | Maximum Marks | Marks Obtained | Percentage |
|---------|---------------|---------------|------------|
| Aim | {scores['aim']['max']} | {scores['aim']['score']:.2f} | {(scores['aim']['score']/scores['aim']['max'])*100:.1f}% |
| Algorithm | {scores['algorithm']['max']} | {scores['algorithm']['score']:.2f} | {(scores['algorithm']['score']/scores['algorithm']['max'])*100:.1f}% |
| Program | {scores['program']['max']} | {scores['program']['score']:.2f} | {(scores['program']['score']/scores['program']['max'])*100:.1f}% |
| Output | {scores['output']['max']} | {scores['output']['score']:.2f} | {(scores['output']['score']/scores['output']['max'])*100:.1f}% |
| Result | {scores['result']['max']} | {scores['result']['score']:.2f} | {(scores['result']['score']/scores['result']['max'])*100:.1f}% |
| *Total* | *{scores['total']['max']}* | *{scores['total']['score']:.2f}* | *{(scores['total']['score']/scores['total']['max'])*100:.1f}%* |

## Detailed Evaluation

### Aim Evaluation
- *Score*: {scores['aim']['score']:.2f}/{scores['aim']['max']}
- *Feedback*: {scores['aim']['explanation']}

### Algorithm Evaluation
- *Score*: {scores['algorithm']['score']:.2f}/{scores['algorithm']['max']}
- *Feedback*: {scores['algorithm']['explanation']}

### Program Evaluation
- *Score*: {scores['program']['score']:.2f}/{scores['program']['max']}
- *Feedback*: {scores['program']['explanation']}

### Output Evaluation
- *Score*: {scores['output']['score']:.2f}/{scores['output']['max']}

### Result Evaluation
- *Score*: {scores['result']['score']:.2f}/{scores['result']['max']}
- *Feedback*: {scores['result']['explanation']}

## Full Evaluation Report

{evaluation_text}


Evaluation performed using automated assessment system.
"""
    return markdown

# =========================
# RUN PIPELINE
# =========================
if _name_ == "_main_":
    try:
        run_pipeline()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Please check your configuration and try again.")