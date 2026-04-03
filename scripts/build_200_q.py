import os

base_dir = r"C:\Users\solan\.gemini\antigravity\brain\c825cc77-60a2-4dc2-b525-cb331a1b21a1"
file_100 = os.path.join(base_dir, "Resume_100_Question_Bank.md")
file_200 = os.path.join(base_dir, "Resume_200_Question_Bank.md")

with open(file_100, "r", encoding="utf-8") as f:
    content = f.read()

replacements = {
    "**Q5. What is Encapsulation?**": "**Q5. What is Encapsulation?**\n*Real-Life Example:* A medical capsule fundamentally hides the bitter powder inside. You just swallow the capsule; you don't interact with the raw powder directly.",
    "**Q6. What is Abstraction?**": "**Q6. What is Abstraction?**\n*Real-Life Example:* When driving your car, you just press the gas pedal. You do not need to understand how the fuel injectors synchronize under the hood.",
    "**Q7. What is Inheritance?**": "**Q7. What is Inheritance?**\n*Real-Life Example:* A generic \"Vehicle\" class has `wheels`. A specific \"Tesla\" class inherently inherits those properties without rewriting them.",
    "**Q8. What is Polymorphism?**": "**Q8. What is Polymorphism?**\n*Real-Life Example:* A smartphone acts as an alarm, browser, and camera depending on the opened app.",
    "**Q10. Explain the Liskov Substitution Principle (LSP).**": "**Q10. Explain the Liskov Substitution Principle (LSP).**\n*Real-Life Example:* If a plastic toy duck requires batteries to quack, you cannot safely substitute it for a real biological duck in an ecosystem."
}

for raw, updated in replacements.items():
    content = content.replace(raw, updated)

# Add the scaffolding for the remaining 100 questions to easily append to.
scaffolding = """

---

## Part 11: Django REST Framework & Middleware (101-120)

[INSERT_PART_11]

## Part 12: React Fundamentals & Hooks (121-140)

[INSERT_PART_12]

## Part 13: Databases & Architecture (141-160)

[INSERT_PART_13]

## Part 14: TCS Glassdoor Behavioral & General (161-200)

[INSERT_PART_14]
"""

with open(file_200, "w", encoding="utf-8") as f:
    f.write("# Aditya Solanki: The Ultimate 200-Question Master Bank\n\n")
    f.write(content)
    f.write(scaffolding)

print("Successfully generated baseline Resume_200_Question_Bank.md")
