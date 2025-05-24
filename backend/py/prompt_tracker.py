import os
import json

STATE_FILE = "prompt_state.json"

def load_prompt_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_prompt_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_used_prompts_for_intent(intent):
    state = load_prompt_state()
    return state.get(intent, {}).get("used_prompts", [])

def add_used_prompt(intent, prompt):
    state = load_prompt_state()
    if intent not in state:
        state[intent] = {"used_prompts": [], "prompts": {}}

    if "used_prompts" not in state[intent]:
        state[intent]["used_prompts"] = []

    if prompt not in state[intent]["used_prompts"]:
        state[intent]["used_prompts"].append(prompt)

    if "prompts" not in state[intent]:
        state[intent]["prompts"] = {}

    if prompt not in state[intent]["prompts"]:
        state[intent]["prompts"][prompt] = {"last_page": 0, "unique_entries": 0, "completed": False}

    save_prompt_state(state)

def get_prompt_progress(prompt):
    state = load_prompt_state()
    for intent_data in state.values():
        if "prompts" in intent_data and prompt in intent_data["prompts"]:
            return intent_data["prompts"][prompt]
    return {"last_page": 0, "unique_entries": 0, "completed": False}

def update_prompt_progress(prompt, new_entries=0):
    state = load_prompt_state()
    for intent, data in state.items():
        if "prompts" in data and prompt in data["prompts"]:
            progress = data["prompts"][prompt]
            progress["last_page"] += 3
            progress["unique_entries"] += new_entries
            if progress["last_page"] >= 10:
                progress["completed"] = True
            save_prompt_state(state)
            return
    # If prompt wasn't found, create new
    add_used_prompt("unknown", prompt)
    update_prompt_progress(prompt, new_entries)

def is_prompt_completed(prompt):
    return get_prompt_progress(prompt)["completed"]
