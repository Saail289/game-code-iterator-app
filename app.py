import streamlit as st
import difflib
from groq import Groq
import re

# Initialize session state
if "original_code" not in st.session_state:
    st.session_state.original_code = ""
if "modified_code" not in st.session_state:
    st.session_state.modified_code = ""
if "explanation" not in st.session_state:
    st.session_state.explanation = ""
if "integrated_code" not in st.session_state:
    st.session_state.integrated_code = ""
if "diff_output" not in st.session_state:
    st.session_state.diff_output = ""
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "prompt_history" not in st.session_state:
    st.session_state.prompt_history = []
if "error_message" not in st.session_state:
    st.session_state.error_message = ""
if "error_fix_suggestion" not in st.session_state:
    st.session_state.error_fix_suggestion = ""
if "language_selection" not in st.session_state:
    st.session_state.language_selection = "C++"
if "error_updated_code" not in st.session_state:
    st.session_state.error_updated_code = ""

# Streamlit app layout
st.title("Game Code Iterator Assistant")
st.markdown("A tool to modify game code based on user prompts, with iterative changes saved in memory.")

# API key input
st.subheader("Enter Groq API Key")
st.markdown("Get your free Groq API key from [console.groq.com/keys](https://console.groq.com/keys).")
api_key_input = st.text_input("Groq API Key", type="password", value=st.session_state.api_key)
if api_key_input:
    st.session_state.api_key = api_key_input.strip()
    if not st.session_state.api_key.startswith("gsk_"):
        st.error("Invalid API key format. It should start with 'gsk_'. Please check and try again.")
        st.session_state.api_key = ""

# Initialize Groq client only if API key is provided
client = None
if st.session_state.api_key:
    try:
        client = Groq(api_key=st.session_state.api_key)
    except Exception as e:
        st.error(f"Failed to initialize Groq client. Please verify your API key: {str(e)}")
        client = None

# Available LLM models on Groq API
models = [
    "llama-3.3-70b-versatile",
    "llama-3-70b-8192",
    "llama-3-8b-8192",
    "llama-3.1-70b-instruct",
    "llama-3.1-8b-instruct",
    "llama-4-scout",
    "llama-4-maverick",
    "mixtral-8x7b-32768",
    "gemma-7b-it",
    "qwen-2.5-32b",
    "deepseek-r1-distill-qwen-32b"
]

# Sidebar for language selection, LLM selection, prompt history, and instructions
if client:
    with st.sidebar:
        # Language selection dropdown (above LLM model selection)
        st.subheader("Select Game Development Language")
        languages = ["C++", "C# (Outside Unity)", "GDScript", "JavaScript", "Python", "Lua", "Haxe", "Rust"]
        selected_language = st.selectbox("Choose a language", languages, index=languages.index(st.session_state.language_selection))
        st.session_state.language_selection = selected_language

        # LLM model selection
        selected_model = st.selectbox("Select LLM Model", models, index=0)
        
        # Prompt History with edit and delete options
        st.subheader("Prompt History")
        if st.session_state.prompt_history:
            for idx, prompt in enumerate(st.session_state.prompt_history):
                col1, col2 = st.columns([4, 1])
                with col1:
                    edited_prompt = st.text_input(f"Step {idx + 1}", prompt, key=f"prompt_{idx}")
                    if edited_prompt != prompt:
                        st.session_state.prompt_history[idx] = edited_prompt
                with col2:
                    if st.button("❌", key=f"delete_{idx}", help="Delete this prompt"):
                        st.session_state.prompt_history.pop(idx)
                        st.experimental_rerun()
        else:
            st.write("No prompts yet. Add a prompt and click 'Generate Suggestions' to start.")
        
        st.markdown("""
        ### How to Use
        1. Enter your Groq API key (get it from [console.groq.com/keys](https://console.groq.com/keys)).
        2. Select a game development language from the dropdown.
        3. Paste your game code in the text area.
        4. Select a template or enter a custom prompt describing the desired changes.
        5. Click "Generate Suggestions" to see modified code and explanations. Prompts are saved in memory for iterative changes.
        6. Edit or delete prompts in the history as needed, then click "Generate Suggestions" to update.
        7. You can repeat steps to make additional changes to the code.
        8. When satisfied, click "Integrate Code" to apply all changes and view the final working code.
        9. Test the final integrated code in the appropriate environment. If you encounter an error, use the troubleshooting section or error reporting feature below.
        """)

# Prompt templates
templates = {
    "Select a task": "",
    "Add jump mechanic": f"Modify this {st.session_state.language_selection} code to add a jump mechanic with height 2 units, triggered by the spacebar (or equivalent input for the chosen language).",
    "Add health system": f"Modify this {st.session_state.language_selection} code to add a health system with max health 100 and a damage function.",
    "Optimize performance": f"Modify this {st.session_state.language_selection} code to improve frame rate, focusing on efficient movement or rendering."
}

# Input section (only shown if API key is valid)
if client:
    st.subheader("Input Game Code and Prompt")
    code_input = st.text_area("Paste your game code here", height=200, placeholder=f"e.g., a {st.session_state.language_selection} class or script for your game...")
    template = st.selectbox("Select a common game task (optional)", list(templates.keys()))
    prompt_input = st.text_input("Describe the changes you want", value=templates[template] if template != "Select a task" else "")
    context_input = st.text_input("Additional context (optional)", placeholder=f"e.g., engine version, components, or {st.session_state.language_selection} specifics")
    generate_button = st.button("Generate Suggestions")
else:
    st.warning("Please enter a valid Groq API key to proceed.")

# Function to validate code based on selected language
def validate_code(code, language):
    if not code.strip():
        return False, "Error: Code input is empty."
    if language == "C++":
        if "std::" not in code and "using namespace std;" not in code and "cout" not in code:
            return False, "Error: Code does not appear to be valid C++. Include standard library usage (e.g., 'using namespace std;' or 'std::cout')."
    elif language == "C# (Outside Unity)":
        if "class" not in code or "{" not in code:
            return False, "Error: Code does not appear to be valid C#. Include a class definition with curly braces."
    elif language == "GDScript":
        if "extends" not in code and "func" not in code:
            return False, "Error: Code does not appear to be valid GDScript. Include 'extends' and 'func' keywords."
    elif language == "JavaScript":
        if "function" not in code and "let" not in code and "const" not in code:
            return False, "Error: Code does not appear to be valid JavaScript. Include function declarations or variable definitions."
    elif language == "Python":
        if "def" not in code and "import" not in code:
            return False, "Error: Code does not appear to be valid Python. Include 'def' for functions or 'import' statements."
    elif language == "Lua":
        if "function" not in code and "local" not in code:
            return False, "Error: Code does not appear to be valid Lua. Include 'function' or 'local' keywords."
    elif language == "Haxe":
        if "class" not in code and "function" not in code:
            return False, "Error: Code does not appear to be valid Haxe. Include 'class' and 'function' keywords."
    elif language == "Rust":
        if "fn" not in code and "struct" not in code:
            return False, "Error: Code does not appear to be valid Rust. Include 'fn' for functions or 'struct' definitions."
    return True, ""

# Function to generate a detailed fallback explanation if the API fails to provide one
def generate_fallback_explanation(original_code, modified_code, prompt_history, language):
    explanation = "### Key Changes Made:\n"
    if "jump" in prompt_history[-1].lower() or "jumpForce" in modified_code.lower():
        explanation += f"- Added a jump mechanic to the {language} code. This allows the player to jump when a specific key (like the spacebar) is pressed. The mechanic uses variables to track the player's vertical position, applies an initial upward velocity, and simulates gravity to bring the player back down.\n"
    if "health" in prompt_history[-1].lower() or "maxHealth" in modified_code.lower():
        explanation += f"- Added a health system to the {language} code. This tracks the player's health, starting at a maximum value (e.g., 100), and includes a function to reduce health when the player takes damage.\n"
    if "optimize" in prompt_history[-1].lower() or "performance" in modified_code.lower():
        explanation += f"- Optimized performance in the {language} code. This might involve reducing unnecessary calculations, improving loop efficiency, or using better data structures to make the game run smoother.\n"
    
    explanation += f"\n### Detailed Step-by-Step Breakdown of the {language} Code:\n"
    # Split the modified code into lines for detailed analysis
    lines = modified_code.split("\n")
    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        if "jump" in prompt_history[-1].lower() and "jump" in line.lower():
            explanation += f"- **Line {idx}: `{line}`** - This line is part of the jump mechanic. It likely checks for a key press (e.g., spacebar) to start the jump or updates the player's vertical position. The reasoning behind this is to allow the player to interact with the game world by jumping over obstacles or reaching higher platforms, which is a core feature in many 2D games.\n"
        elif "health" in prompt_history[-1].lower() and "health" in line.lower():
            explanation += f"- **Line {idx}: `{line}`** - This line relates to the health system. It might define the player's health or reduce it when damage is taken. The purpose is to track the player's survival status, adding challenge and strategy to the game by requiring the player to avoid damage.\n"
        elif line.startswith(("def ", "function ", "void ", "fn ", "class ", "struct ")):
            explanation += f"- **Line {idx}: `{line}`** - This line defines a function or method in {language}. Functions are used to organize code into reusable blocks, making it easier to manage game logic like updating the player's position or handling input.\n"
        elif "=" in line and "if" not in line:
            explanation += f"- **Line {idx}: `{line}`** - This line initializes a variable. Variables store important game data, such as the player's position or speed, which are used to control how the game behaves.\n"
        elif "if " in line:
            explanation += f"- **Line {idx}: `{line}`** - This line contains a conditional statement. It checks for a condition (e.g., a key press) and executes code if the condition is true, which is essential for handling player input and game events.\n"
    
    explanation += f"\n### Reasoning Behind the Changes:\n"
    if "jump" in prompt_history[-1].lower():
        explanation += f"- **Jump Mechanic**: The jump mechanic was added to enhance gameplay by allowing vertical movement. In {language}, this typically involves checking for a key press (e.g., spacebar) to start the jump, applying an upward velocity to the player's position, and using gravity to bring the player back down. This creates a smooth jumping effect, making the game more interactive and fun. The variables like `jump_velocity` and `gravity` are carefully chosen to balance the jump height and fall speed, ensuring the player can jump over obstacles without the jump feeling too floaty or too abrupt.\n"
    elif "health" in prompt_history[-1].lower():
        explanation += f"- **Health System**: The health system was added to introduce a survival element to the game. By tracking the player's health, the game can simulate damage from enemies or obstacles, making the player more cautious. The `max_health` variable sets the starting health, and a damage function allows the health to decrease, adding challenge and stakes to the gameplay.\n"
    elif "optimize" in prompt_history[-1].lower():
        explanation += f"- **Performance Optimization**: The optimization changes were made to improve the game's frame rate, ensuring it runs smoothly even on lower-end devices. In {language}, this might involve reducing the number of calculations in the game loop or using more efficient data structures, which helps maintain a consistent gaming experience.\n"
    
    explanation += f"\n### How the {language} Code Fits into Game Development:\n"
    explanation += f"- The modified code follows {language} best practices, making it suitable for game development in its respective environment (e.g., using Pygame for Python). The changes enhance the player's experience by adding interactive features like jumping, while maintaining the core game loop that updates the game state each frame.\n"
    return explanation

# Function to call Groq API with prompt history and language context
def generate_code_modification(code, prompt_history, context, model, language):
    system_prompt = f"""
    You are an expert game developer proficient in {language}. Modify the provided code based on the sequence of user prompts, ensuring best practices for {language} in game development (e.g., memory management for C++, dynamic typing for Python, Rigidbody for C#). Apply each prompt in order, building on the previous modifications. Return the response in markdown format:
    ```{language.lower()}
    [modified code]
    ```
    **Explanation**: Provide a highly detailed, elaborative, and beginner-friendly explanation of the modified code. Ensure the explanation is easy to understand for someone new to {language} and game development. Avoid generic responses and focus on specifics of the code. Include the following sections:
    - **Summary of Changes**: Summarize all changes made to the original code across all prompts in a clear list, explaining what was added or modified.
    - **How the New Features Work**: Explain each new or modified feature in detail, specific to {language} and its game development context (e.g., how a jump mechanic works with physics or input handling in {language}).
    - **Step-by-Step Code Breakdown**: Break down the entire modified code line by line, explaining the purpose of each variable, function, and language-specific feature (e.g., what a loop does, why a variable is initialized, how the game loop interacts with the feature). Include reasoning for why each line is necessary for the game.
    - **Game Logic Explained**: Describe how the changes fit into the broader game logic, such as how the feature affects gameplay (e.g., how a health system impacts player survival).
    - **If a Prompt is a Duplicate**: Note that no additional changes were made for that step.
    """
    # Combine all prompts into a single user prompt, showing the history
    user_prompt = f"""
    Context: {context or f'No additional context provided for {language}.'}
    Original code:
    ```{language.lower()}
    {code}
    ```
    Apply the following changes in sequence:
    """
    for idx, prompt in enumerate(prompt_history, 1):
        user_prompt += f"\nStep {idx}: {prompt}"
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1500
    )
    output = response.choices[0].message.content
    st.write("Debug: Raw LLM Response for Code Modification:", output)  # Debug output
    
    # Parse response
    code_match = re.search(rf"```{language.lower()}\n(.*?)```", output, re.DOTALL)
    explanation_match = re.search(r"\*\*Explanation\*\*:(.*?)$", output, re.DOTALL)
    modified_code = code_match.group(1).strip() if code_match else ""
    explanation = explanation_match.group(1).strip() if explanation_match else ""
    
    # Fallback if explanation is empty or insufficient
    if not explanation or explanation == "No explanation provided." or len(explanation.split("\n")) < 5:  # If explanation is too short
        explanation = generate_fallback_explanation(code, modified_code, prompt_history, language)
    
    return modified_code, explanation

# Function to suggest fixes for errors and provide updated code
def suggest_error_fix(error_message, code, model, language):
    system_prompt = f"""
    You are an expert game developer proficient in {language}. The user has encountered an error while testing their {language} game code. Analyze the error message and the code, then provide:
    1. A clear, beginner-friendly suggestion to fix the error, specific to {language} game development.
    2. The fully updated code with the fix applied.
    Return the response in markdown format:
    **Suggested Fix**: [Detailed explanation of the fix, including why the error occurred, how the fix resolves it, and any code changes made.]
    **Updated Code**:
    ```{language.lower()}
    [fully updated code with the fix applied]
    ```
    """
    user_prompt = f"""
    Error message from the game environment:
    {error_message}

    Code being tested:
    ```{language.lower()}
    {code}
    ```
    Suggest a fix for this error and provide the fully updated code.
    """
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    output = response.choices[0].message.content
    st.write("Debug: Raw LLM Response for Error Fix:", output)
    
    fix_suggestion_match = re.search(r"\*\*Suggested Fix\*\*:(.*?)\*\*Updated Code\*\*:", output, re.DOTALL)
    updated_code_match = re.search(rf"```{language.lower()}\n(.*?)```", output, re.DOTALL)
    
    fix_suggestion = fix_suggestion_match.group(1).strip() if fix_suggestion_match else "Unable to suggest a fix. Please check the error message and code for typos or missing components."
    updated_code = updated_code_match.group(1).strip() if updated_code_match else code
    
    return fix_suggestion, updated_code

# Function to compute diff (kept for potential future use, but not displayed)
def compute_diff(original, modified):
    diff = difflib.unified_diff(original.splitlines(), modified.splitlines(), lineterm="")
    return "\n".join(diff)

# Handle generation
if client and generate_button and code_input and prompt_input:
    # If this is the first prompt, set the original code
    if not st.session_state.prompt_history and not st.session_state.original_code:
        st.session_state.original_code = code_input
    # Append the new prompt to history
    previous_length = len(st.session_state.prompt_history)
    st.session_state.prompt_history.append(prompt_input)
    try:
        # Use the original code as the base, and apply all prompts in sequence
        modified_code, explanation = generate_code_modification(
            st.session_state.original_code, st.session_state.prompt_history, context_input, selected_model, st.session_state.language_selection
        )
        is_valid, validation_error = validate_code(modified_code, st.session_state.language_selection)
        if not is_valid:
            st.error(validation_error)
        else:
            st.session_state.modified_code = modified_code
            st.session_state.explanation = explanation
            st.session_state.diff_output = compute_diff(st.session_state.original_code, modified_code)
            # Force a rerun if this is the first prompt to ensure the sidebar updates
            if previous_length == 0:
                st.experimental_rerun()
    except Exception as e:
        st.error(f"Error generating suggestions: {str(e)}")

# Display suggestions
if st.session_state.modified_code:
    st.subheader("Suggested Changes")
    st.markdown("**Suggested Code**")
    st.code(st.session_state.modified_code, language=st.session_state.language_selection.lower())
    st.markdown("**Detailed Explanation of Changes**")
    st.markdown(st.session_state.explanation)
    
    # Integrate button
    if st.button("Integrate Code"):
        st.session_state.integrated_code = st.session_state.modified_code
        st.session_state.diff_output = compute_diff(st.session_state.original_code, st.session_state.integrated_code)
        # Clear prompt history after integration
        st.session_state.prompt_history = []

# Display final output
if st.session_state.integrated_code:
    st.subheader("Final Integrated Code")
    st.code(st.session_state.integrated_code, language=st.session_state.language_selection.lower())
    st.markdown("Test the integrated code in the appropriate environment to see the changes in action.")
    
    # Troubleshooting section
    st.subheader("Troubleshooting Common Errors")
    
    # Error reporting feature
    st.subheader("Report an Error")
    st.markdown("If you encountered an error, paste the error message below and click 'Suggest Fix' to get help.")
    error_message = st.text_area("Paste the error message here", value=st.session_state.error_message, height=100)
    if st.button("Suggest Fix") and error_message:
        st.session_state.error_message = error_message
        try:
            fix_suggestion, updated_code = suggest_error_fix(error_message, st.session_state.integrated_code, selected_model, st.session_state.language_selection)
            st.session_state.error_fix_suggestion = fix_suggestion
            st.session_state.error_updated_code = updated_code
            st.session_state.integrated_code = updated_code
        except Exception as e:
            st.error(f"Error suggesting fix: {str(e)}")
            st.session_state.error_fix_suggestion = "Unable to suggest a fix due to an error. Please check the error message and code manually."
            st.session_state.error_updated_code = st.session_state.integrated_code
    
    if st.session_state.error_fix_suggestion:
        st.markdown("**Suggested Fix**")
        st.markdown(st.session_state.error_fix_suggestion)
        st.markdown("**Updated Code After Fix**")
        st.code(st.session_state.error_updated_code, language=st.session_state.language_selection.lower())