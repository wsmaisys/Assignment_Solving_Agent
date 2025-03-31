import requests

def send_request(question, file_path=None):
    """Send a POST request to the mistral_agent.py endpoint."""
    url = "http://localhost:8000/submit"
    data = {"question": question}
    files = {"file": open(file_path, "rb")} if file_path else None

    try:
        response = requests.post(url, data=data, files=files)
        print("Question:", question)
        print("Response:", response.json())
    except Exception as e:
        print("Error:", str(e))
    finally:
        if files:
            files["file"].close()

if __name__ == "__main__":
    # Example 1: Extract the value in the "answer" column of the CSV file
    send_request(
        "Unzip file q-extract-csv-zip.zip which has a single extract.csv file inside. What is the value in the answer column of the CSV file?",
        "uploads/q-extract-csv-zip.zip"
    )

    # Example 2: Count the number of Wednesdays in a date range
    send_request(
        "How many Wednesdays are there in the date range 1989-04-21 to 2017-10-01?"
    )

    # Example 3: Sort a JSON array by age and name
    send_request(
        "Sort this JSON array of objects by the value of the age field. In case of a tie, sort by the name field. Paste the resulting JSON below without any spaces or newlines."
    )

    # Example 4: Sum values across multiple CSV files with different encodings
    send_request(
        "Process the files in q-unicode-data.zip which contains three files with different encodings: data1.csv (CP-1252), data2.csv (UTF-8), and data3.txt (UTF-16). Each file has 2 columns: symbol and value. Sum up all the values where the symbol matches – OR ‡ OR Ž across all three files. What is the sum of all values associated with these symbols?",
        "test_files/q-unicode-data.zip"
    )

    # Example 5: Replace text in files and verify the hash
    send_request(
        "See q-replace-across-files.zip and unzip it into a new folder, then replace all 'IITM' (in upper, lower, or mixed case) with 'IIT Madras' in all files. Leave everything as-is - don't change the line endings. What does running cat * | sha256sum in that folder show in bash?",
        "test_files/q-replace-across-files.zip"
    )

    # Example 6: List files and filter by size and modification date
    send_request(
        "Download q-list-files-attributes.zip and extract it. Use ls with options to list all files in the folder along with their date and file size. What's the total size of all files at least 9338 bytes large and modified on or after Thu, 27 Oct, 2016, 8:32 am IST?",
        "test_files/q-list-files-attributes.zip"
    )

    # Example 7: Move and rename files
    send_request(
        "Download q-move-rename-files.zip and extract it. Use mv to move all files under folders into an empty folder. Then rename all files replacing each digit with the next. 1 becomes 2, 9 becomes 0, a1b9c.txt becomes a2b0c.txt. What does running grep . * | LC_ALL=C sort | sha256sum in bash on that folder show?",
        "test_files/q-move-rename-files.zip"
    )

    # Example 8: Calculate the total Economics marks of students who scored 78 or more in Maths in groups 73-93
    send_request(
        "This file q-extract-tables-from-pdf.pdf contains a table of student marks in Maths, Physics, English, Economics, and Biology. Calculate the total Economics marks of students who scored 78 or more marks in Maths in groups 73-93 (including both groups).",
        "test_files/q-extract-tables-from-pdf.pdf"
    )

    # Example 9: Count the number of unique students in the file
    send_request(
        "This file q-clean-up-student-marks.txt contains student marks. Count the number of unique students based on their student IDs.",
        "test_files/q-clean-up-student-marks.txt"
    )

    # Example 10: Extract and sum values from a JSON file
    send_request(
        "This file q-parse-partial-json.jsonl contains sales data. Calculate the total sales value.",
        "test_files/q-parse-partial-json.jsonl"
    )

    # Example 11: Extract and process nested JSON keys
    send_request(
        "This file q-extract-nested-json-keys.json contains nested JSON data. How many times does the key 'UO' appear as a key in the JSON structure?",
        "test_files/q-extract-nested-json-keys.json"
    )

    # Example 12: Analyze Apache log file for specific requests
    send_request(
        "This file s-anand.net-May-2024.gz contains Apache logs. How many successful GET requests for pages under /hindi/ were made on Tuesday between 15:00 and 21:00 during May 2024?",
        "test_files/s-anand.net-May-2024.gz"
    )

    # Example 13: Analyze Apache log file for top data consumer
    send_request(
        "This file s-anand.net-May-2024.gz contains Apache logs. Across all requests under /telugu/ on 2024-05-08, how many bytes did the top IP address (by volume of downloads) download?",
        "test_files/s-anand.net-May-2024.gz"
    )

    # Example 14: Process Excel sales data
    send_request(
        "This file q-clean-up-excel-sales-data.xlsx contains messy sales data. Calculate the total margin for transactions before Wed Jun 15 2022 18:04:00 GMT+0530 (India Standard Time) for Epsilon sold in IN (which may be spelt in different ways).",
        "test_files/q-clean-up-excel-sales-data.xlsx"
    )

    # Example 15: Process JSON sales data
    send_request(
        "This file q-clean-up-sales-data.json contains sales data. How many units of Pants were sold in Chennai on transactions with at least 64 units?",
        "test_files/q-clean-up-sales-data.json"
    )

    # Example 16: Reconstruct scrambled image
    send_request(
        "This file jigsaw.webp contains a scrambled image. Reconstruct the original image using the provided mapping file.",
        "test_files/jigsaw.webp"
    )

    # Example 17: Extract tables from PDF and calculate hash
    send_request(
        "This file q-pdf-to-markdown.pdf contains a document. Convert the PDF to Markdown and format it using Prettier 3.4.2. What is the formatted Markdown content?",
        "test_files/q-pdf-to-markdown.pdf"
    )

    # Example 18: Analyze Hacker News posts for a specific topic
    send_request(
        "Search using the Hacker News RSS API for the latest Hacker News post mentioning Tor and having a minimum of 98 points. What is the link that it points to?"
    )

    # Example 19: Identify newest GitHub user in a location
    send_request(
        "Using the GitHub API, find all users located in the city Hyderabad with over 140 followers. When was the newest user's GitHub profile created?"
    )

    # Example 20: Create a scheduled GitHub action
    send_request(
        "Create a scheduled GitHub action that runs daily and adds a commit to your repository. The workflow should include a step with your email 24ds3000090@ds.study.iitm.ac.in in its name. What is your repository URL?"
    )

    # Example 21: Extract table data from a PDF
    send_request(
        "This file q-extract-tables-from-pdf.pdf contains a table of student marks. Calculate the total Economics marks of students who scored 78 or more marks in Maths in groups 73-93 (including both groups).",
        "test_files/q-extract-tables-from-pdf.pdf"
    )

    # Example 22: Process OCR data for unique student IDs
    send_request(
        "This file q-clean-up-student-marks.txt contains student marks. Count the number of unique students based on their student IDs.",
        "test_files/q-clean-up-student-marks.txt"
    )

    # Example 23: Analyze Apache logs for GET requests
    send_request(
        "This file s-anand.net-May-2024.gz contains Apache logs. How many successful GET requests for pages under /hindi/ were made on Tuesday between 15:00 and 21:00 during May 2024?",
        "test_files/s-anand.net-May-2024.gz"
    )

    # Example 24: Analyze Apache logs for top data consumer
    send_request(
        "This file s-anand.net-May-2024.gz contains Apache logs. Across all requests under /telugu/ on 2024-05-08, how many bytes did the top IP address (by volume of downloads) download?",
        "test_files/s-anand.net-May-2024.gz"
    )

    # Example 25: Process messy sales data
    send_request(
        "This file q-clean-up-excel-sales-data.xlsx contains messy sales data. Calculate the total margin for transactions before Wed Jun 15 2022 18:04:00 GMT+0530 (India Standard Time) for Epsilon sold in IN (which may be spelt in different ways).",
        "test_files/q-clean-up-excel-sales-data.xlsx"
    )

    # Example 26: Process JSON sales data
    send_request(
        "This file q-clean-up-sales-data.json contains sales data. How many units of Pants were sold in Chennai on transactions with at least 64 units?",
        "test_files/q-clean-up-sales-data.json"
    )

    # Example 27: Reconstruct scrambled image
    send_request(
        "This file jigsaw.webp contains a scrambled image. Reconstruct the original image using the provided mapping: .",
        "test_files/jigsaw.webp"
    )