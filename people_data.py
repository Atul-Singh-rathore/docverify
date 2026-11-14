import csv

data = [
    [1, "Aarav Sharma", "14-05-2002", "Male", "+91-9876543210", "Lucknow", "Verified", "96.8%"],
    [2, "Priya Verma", "22-09-2001", "Female", "+91-9123456789", "Kanpur", "Verified", "94.2%"],
    [3, "Rahul Gupta", "05-12-2000", "Male", "+91-9988776655", "Delhi", "Verified", "95.5%"],
    [4, "Sneha Singh", "18-03-2003", "Female", "+91-9811223344", "Lucknow", "Pending", "88.1%"],
    [5, "Amit Kumar", "30-07-1999", "Male", "+91-9722334455", "Patna", "Verified", "97.3%"],
    [6, "Ananya Mishra", "11-11-2002", "Female", "+91-9633445566", "Varanasi", "Verified", "92.9%"],
    [7, "Rohit Verma", "03-01-2001", "Male", "+91-9544556677", "Gorakhpur", "Failed", "64.5%"],
    [8, "Neha Pandey", "25-06-2000", "Female", "+91-9455667788", "Agra", "Verified", "96.1%"],
    [9, "Vikas Yadav", "14-08-1998", "Male", "+91-9366778899", "Meerut", "Verified", "95.0%"],
    [10, "Pooja Tiwari", "09-02-2003", "Female", "+91-9277889900", "Bareilly", "Verified", "91.8%"],
    [11, "Karan Malhotra", "19-10-2001", "Male", "+91-9188990011", "Noida", "Verified", "98.2%"],
    [12, "Shreya Sen", "07-04-2002", "Female", "+91-9099001122", "Ghaziabad", "Verified", "94.7%"],
    [13, "Mohit Chauhan", "12-12-1999", "Male", "+91-9888112233", "Aligarh", "Pending", "85.3%"],
    [14, "Divya Joshi", "28-05-2000", "Female", "+91-9777223344", "Jhansi", "Verified", "96.4%"],
    [15, "Saurabh Dubey", "16-09-2001", "Male", "+91-9666334455", "Mathura", "Verified", "93.6%"],
    [16, "Ritu Saxena", "04-07-2002", "Female", "+91-9555445566", "Saharanpur", "Verified", "95.8%"],
    [17, "Manish Tiwari", "21-01-2000", "Male", "+91-9444556677", "Ayodhya", "Failed", "59.2%"],
    [18, "Tanvi Agarwal", "13-03-2003", "Female", "+91-9333667788", "Moradabad", "Verified", "97.1%"],
    [19, "Akash Verma", "30-10-2001", "Male", "+91-9222778899", "Shahjahanpur", "Verified", "92.4%"],
    [20, "Kirti Sinha", "08-08-2000", "Female", "+91-9111889900", "Rampur", "Verified", "96.9%"],
]

headers = ["S.No.", "Full Name", "DOB", "Gender", "Contact Number", "City", "Status", "Confidence Score"]

with open("dummy_applicants.csv", mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(data)

print("✅ dummy_applicants.csv successfully created")
