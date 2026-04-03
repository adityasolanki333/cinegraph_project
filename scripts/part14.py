import os

file_200 = r"C:\Users\solan\.gemini\antigravity\brain\c825cc77-60a2-4dc2-b525-cb331a1b21a1\Resume_200_Question_Bank.md"

with open(file_200, "r", encoding="utf-8") as f:
    content = f.read()

db_data_cont = [
    ("Q146. What is ACID?", "Atomicity, Consistency, Isolation, explicitly Durability."),
    ("Q147. What is Database Normalization?", "Restructuring DB schemas to drastically reduce data redundancy."),
    ("Q148. What is a Foreign Key Constraint?", "A strict backend rule formally enforcing referential table integrity."),
    ("Q149. Explain NoSQL vs SQL.", "SQL stores structured relational tables. NoSQL dynamically stores raw JSON-like documents without rigid schemas."),
    ("Q150. Why PostgreSQL for Django?", "It explicitly supports advanced ArrayFields and provides massive scaling for heavy traffic seamlessly."),
    ("Q151. What is a CrossEncoder?", "An AI model computing text similarity accurately."),
    ("Q152. Explain Cosine Similarity.", "A metric evaluating the angle between two mathematical vectors.")
]

glassdoor_behavioral = [
    ("Q153. Why TCS?", "TCS is an undisputed global IT leader. Working here provides unparalleled enterprise exposure."),
    ("Q154. What are your greatest strengths?", "My strict ability to continuously learn complex new technologies, like when I independently learned Vector Databases for CineGraph."),
    ("Q155. Tell me about a time you showed leadership.", "During the Science Exhibition, I architected a Home Security Laser Alarm specifically coordinating a small team to execute the physical wiring flawlessly."),
    ("Q156. How do you handle stressful tight deadlines?", "I immediately break the massive project down into strict atomic JIRA tasks mathematically to ensure daily incremental progress."),
    ("Q157. What is Agile Methodology?", "An iterative software development lifecycle. We build software in small sprints instead of one massive monolithic release."),
    ("Q158. What is a Sprint in Agile?", "A timeboxed 2-week development cycle where the team formally commits to finishing specific features."),
    ("Q159. Are you willing to relocate?", "Absolutely. I am highly flexible and excited to completely relocate to whichever TCS branch officially requires my technical stack."),
    ("Q160. Why did you explicitly build Cinema-Guide (CineGraph)?", "I built it to solve 'movie choice paralysis'. Netflix algorithmically forces generic popularity-based trends. I wanted a highly personalized semantic vector-search engine where users can natively search abstract, highly specific plot concepts safely securely intelligently cleanly and get exact matches dynamically.")
]

def format_block(data):
    lines = []
    for q, a in data:
        lines.append(f"**{q}**\n{a}\n")
    return "\n".join(lines)

content = content.replace("[INSERT_PART_13]", format_block(db_data_cont))
content = content.replace("[INSERT_PART_14]", format_block(glassdoor_behavioral))

with open(file_200, "w", encoding="utf-8") as f:
    f.write(content)

print("done")
