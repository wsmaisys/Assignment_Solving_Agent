import requests
import os

def send_request(url, question, file_path=None):
    """
    Send a POST request with a question and optional file.

    Args:
        url (str): The URL of the API endpoint.
        question (str): The question to be sent.
        file_path (str, optional): The path to the file to be sent. Defaults to None.

    Returns:
        response: The response from the API endpoint.
    """
    # Prepare the data for the request
    data = {"question": question}

    # Prepare the files for the request
    files = {}
    if file_path and os.path.isfile(file_path):
        files = {"file": open(file_path, "rb")}

    # Send the POST request
    response = requests.post(url, data=data, files=files)

    # Close the file if it was opened
    if file_path and os.path.isfile(file_path):
        files["file"].close()

    return response

if __name__ == "__main__":
    # Define the API URL
    url = "http://localhost:8000/submit"

    # List of questions and corresponding files
    questions_files = [
        {
            "question": "Unzip file q-extract-csv-zip.zip which has a single extract.csv file inside. What is the value in the answer column of the CSV file?",
            "file": "uploads/q-extract-csv-zip.zip"
        },
        {
            "question": "How many Wednesdays are there in the date range 1989-04-21 to 2017-10-01?",
            "file": None
        },
        {
            "question": "Sort this JSON array of objects by the value of the age field. In case of a tie, sort by the name field. Paste the resulting JSON below without any spaces or newlines.",
            "file": None
        },
        {
            "question": "Process the files in q-unicode-data.zip which contains three files with different encodings: data1.csv (CP-1252), data2.csv (UTF-8), and data3.txt (UTF-16). Each file has 2 columns: symbol and value. Sum up all the values where the symbol matches – OR ‡ OR Ž across all three files. What is the sum of all values associated with these symbols?",
            "file": "test_files/q-unicode-data.zip"
        },
        {
            "question": "See q-replace-across-files.zip and unzip it into a new folder, then replace all 'IITM' (in upper, lower, or mixed case) with 'IIT Madras' in all files. Leave everything as-is - don't change the line endings. What does running cat * | sha256sum in that folder show in bash?",
            "file": "test_files/q-replace-across-files.zip"
        },
        {
            "question": "Download q-list-files-attributes.zip and extract it. Use ls with options to list all files in the folder along with their date and file size. What's the total size of all files at least 9338 bytes large and modified on or after Thu, 27 Oct, 2016, 8:32 am IST?",
            "file": "test_files/q-list-files-attributes.zip"
        },
        {
            "question": "Download q-move-rename-files.zip and extract it. Use mv to move all files under folders into an empty folder. Then rename all files replacing each digit with the next. 1 becomes 2, 9 becomes 0, a1b9c.txt becomes a2b0c.txt. What does running grep . * | LC_ALL=C sort | sha256sum in bash on that folder show?",
            "file": "test_files/q-move-rename-files.zip"
        },
        {
            "question": "This file q-extract-tables-from-pdf.pdf contains a table of student marks in Maths, Physics, English, Economics, and Biology. Calculate the total Economics marks of students who scored 78 or more marks in Maths in groups 73-93 (including both groups).",
            "file": "test_files/q-extract-tables-from-pdf.pdf"
        },
        {
            "question": "This file q-clean-up-student-marks.txt contains student marks. Count the number of unique students based on their student IDs.",
            "file": "test_files/q-clean-up-student-marks.txt"
        },
        {
            "question": "This file q-parse-partial-json.jsonl contains sales data. Calculate the total sales value.",
            "file": "test_files/q-parse-partial-json.jsonl"
        },
        {
            "question": "This file q-extract-nested-json-keys.json contains nested JSON data. How many times does the key 'UO' appear as a key in the JSON structure?",
            "file": "test_files/q-extract-nested-json-keys.json"
        },
        {
            "question": "This file s-anand.net-May-2024.gz contains Apache logs. How many successful GET requests for pages under /hindi/ were made on Tuesday between 15:00 and 21:00 during May 2024?",
            "file": "test_files/s-anand.net-May-2024.gz"
        },
        {
            "question": "This file s-anand.net-May-2024.gz contains Apache logs. Across all requests under /telugu/ on 2024-05-08, how many bytes did the top IP address (by volume of downloads) download?",
            "file": "test_files/s-anand.net-May-2024.gz"
        },
        {
            "question": "This file q-clean-up-excel-sales-data.xlsx contains messy sales data. Calculate the total margin for transactions before Wed Jun 15 2022 18:04:00 GMT+0530 (India Standard Time) for Epsilon sold in IN (which may be spelt in different ways).",
            "file": "test_files/q-clean-up-excel-sales-data.xlsx"
        },
        {
            "question": "This file q-clean-up-sales-data.json contains sales data. How many units of Pants were sold in Chennai on transactions with at least 64 units?",
            "file": "test_files/q-clean-up-sales-data.json"
        },
        {
            "question": "This file jigsaw.webp contains a scrambled image. Reconstruct the original image using the provided mapping file.",
            "file": "test_files/jigsaw.webp"
        },
        {
            "question": "This file q-pdf-to-markdown.pdf contains a document. Convert the PDF to Markdown and format it using Prettier 3.4.2. What is the formatted Markdown content?",
            "file": "test_files/q-pdf-to-markdown.pdf"
        },
        {
            "question": "Search using the Hacker News RSS API for the latest Hacker News post mentioning Tor and having a minimum of 98 points. What is the link that it points to?",
            "file": None
        },
        {
            "question": "Using the GitHub API, find all users located in the city Hyderabad with over 140 followers. When was the newest user's GitHub profile created?",
            "file": None
        },
        {
            "question": "Create a scheduled GitHub action that runs daily and adds a commit to your repository. The workflow should include a step with your email 24ds3000090@ds.study.iitm.ac.in in its name. What is your repository URL?",
            "file": None
        },
    ]

    # Send requests for each question
    for item in questions_files:
        question = item["question"]
        file_path = item["file"]
        
        response = send_request(url, question, file_path)
        
        print(f"Response for question: '{question}'")
        print(response.text)
        print("-" * 80)