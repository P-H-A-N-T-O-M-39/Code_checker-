✅ GenAI Code Checker

An AI-powered code evaluation system built with Python, OCR, and Generative AI.
This project helps educators evaluate programming assignments from images, PDFs, or text submissions by extracting code, validating it, and generating automated marking reports with detailed feedback.

🚀 Features

🤖 AI-Powered Evaluation – Uses Generative AI to analyze student code quality & correctness.
📑 Structured Breakdown – Splits submission into Aim, Algorithm, Program, Output, and Result.
🛠 Code Validation – Detects syntax errors and logical mistakes automatically.
📊 Marking Scheme – Assigns marks: Aim (10), Algorithm (15), Program (50), Output (15), Result (10).
📉 Mistake Penalty – Deducts marks for detected issues.
📜 Detailed Report – Provides scores with feedback on problem-solving, logic, readability, and effort.

🗂 Project Structure
genai_code_checker/
├── main.py                 # Main pipeline
├── requirements.txt        # Dependencies
├── utils/
│   ├── ocr_utils.py        # OCR & PDF processing
│   ├── eval_utils.py       # AI evaluation logic
│   └── validation.py       # Code validation & mistakes
├── docs/
│   └── README.md           # Documentation
└── samples/
    ├── input_image.jpg     # Example student submission
    └── output_report.txt   # Example evaluation report

⚡ Workflow

Teacher uploads text, image, or PDF of student’s submission.

OCR extracts content → Splits into Aim, Algorithm, Program, Output, Result.

Code is validated for syntax & logical errors.

AI evaluates submission & assigns marks per section.

Mistakes are deducted → Final score generated.

Teacher gets a detailed evaluation report.

🛠 Installation & Setup
1. Clone the Repository
git clone https://github.com/yourusername/genai_code_checker.git
cd genai_code_checker

2. Install Dependencies
pip install -r requirements.txt

3. Run the Tool
python main.py

📡 Tech Stack

Language: Python

OCR: Tesseract, pdf2image

AI/LLM: Generative AI (GPT/Gemini, optional offline evaluation)

Validation: Python ast module for syntax checks

📌 Example Usage

Input (Student Submission):

Aim: Write a Python program to check prime numbers
Algorithm: Divide by numbers from 2 to n-1
Program:
n = 10
for i in range(2, n):
    if n % i == 0:
        print("Not Prime")
        break
else:
    print("Prime")
Output: Not Prime
Result: Program works correctly


Generated Report:

✅ Aim (10/10) – Clearly stated
✅ Algorithm (13/15) – Steps correct but not optimized
⚠ Program (45/50) – Works but variable naming could improve
✅ Output (15/15) – Correct result
✅ Result (10/10) – Matches expected

Total Score: 93/100

⚠ Disclaimer

This project is for educational purposes only.
It is meant to assist teachers in grading assignments, not to fully replace human evaluation.

👩‍💻 Contributors

Mahesh Kumar P
Narendran C M
Melchizedek I
Kishore M
Matthew Lessley Steward R S
Nithish A
Mohammed Jubair A
