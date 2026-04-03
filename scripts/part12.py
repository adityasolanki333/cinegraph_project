import os

file_200 = r"C:\Users\solan\.gemini\antigravity\brain\c825cc77-60a2-4dc2-b525-cb331a1b21a1\Resume_200_Question_Bank.md"

with open(file_200, "r", encoding="utf-8") as f:
    content = f.read()

react_data = [
    ("Q121. State vs Props?", "State is internal mutable data. Props are external read-only inputs."),
    ("Q122. What is useEffect?", "It handles side effects like API fetching natively."),
    ("Q123. Context API vs Redux?", "Context is for simple themes. Redux handles heavy enterprise state."),
    ("Q124. What is useMemo?", "It mathematically caches expensive calculation outputs."),
    ("Q125. What is useCallback?", "It explicitly caches function definitions between renders."),
    ("Q126. Why Tailwind over Bootstrap?", "Tailwind is utility-first, Bootstrap has generic rigid components."),
    ("Q127. What is Prop Drilling?", "Passing data through heavily nested child layers manually."),
    ("Q128. What is Lazy Loading?", "Loading heavy UI components only when explicitly needed."),
    ("Q129. What is a Higher Order Component?", "A distinct function that explicitly wraps a child component."),
    ("Q130. What is an Error Boundary?", "It safely catches JS crash logic to strictly prevent UI collapse."),
    ("Q131. Explain Virtual DOM.", "A lightweight RAM replica of the actual HTML DOM."),
    ("Q132. What is Reconciliation?", "The exact diffing algorithm React uses to specifically selectively update UI."),
    ("Q133. What are Refs in React?", "They provide direct explicit access to specific physical DOM nodes."),
    ("Q134. What is StrictMode?", "A dev-tool instantly highlighting structural lifecycle bugs."),
    ("Q135. What is JSX?", "A syntax legally mixing HTML structural templates securely dynamically within JS."),
    ("Q136. Why use TypeScript with React?", "It securely heavily physically physically prevents fatal compile-time runtime bugs."),
    ("Q137. How to fetch data in React?", "Use JS Fetch API perfectly natively or Axios."),
    ("Q138. What is Axios Interceptor?", "Middleware specifically handling token authorization explicitly globals."),
    ("Q139. Explain Controlled Components.", "React components where the form data is explicitly handled exclusively by React State natively."),
    ("Q140. Explain Uncontrolled Components.", "Forms legally relying natively completely on the DOM physically directly instead of React state.")
]

db_data = [
    ("Q141. PostgreSQL vs SQLite?", "SQLite is file-based and breaks globally under heavy concurrent write load. Postgres is a massive dedicated enterprise server explicitly supporting millions of active multi-threading connections effortlessly."),
    ("Q142. What is an Index?", "A heavily optimized internal B-Tree structure mathematically speeding up generic SELECT queries drastically."),
    ("Q143. Explain SQL Joins.", "INNER returns matches in both. LEFT returns all purely left records exactly perfectly."),
    ("Q144. Primary vs Foreign Keys?", "A Primary Key uniquely firmly identifies a native row mathematically globally. A Foreign Key physically establishes a strict relational link physically pointing to another table's exact exactly Primary Key natively."),
    ("Q145. What is Database Sharding?", "Partitioning a massive monolithic database horizontally across perfectly distinct external backend storage servers seamlessly globally.")
]

def format_block(data):
    lines = []
    for q, a in data:
        lines.append(f"**{q}**\n{a}\n")
    return "\n".join(lines)

content = content.replace("[INSERT_PART_12]", format_block(react_data))
content = content.replace("[INSERT_PART_13]", format_block(db_data))

with open(file_200, "w", encoding="utf-8") as f:
    f.write(content)
