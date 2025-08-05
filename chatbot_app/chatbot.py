# Import the libraries
import os, json, ast, re
import pandas as pd
import openai
from openai import OpenAI
from typing import List, Dict, Union, Any

# Read key from text file
with open("openai_key.txt", "r") as f:
    api_key = f.read().strip()


# Pass key to OpenAI client
client = OpenAI(api_key=api_key)

# Read the dataset and read the Laptop Dataset
dubai_tourist_spots = pd.read_csv('dubai_tours.csv')
dubai_tourist_spots.head()

def initialize_conversation():
    """
    Returns a rich initial prompt including:
    - A system message defining assistant personality and constraints
    - Multiple few-shot examples that demonstrate reasoning
    - Sets context for consistent user interaction
    """

    initial_system_prompt = {
        "role": "system",
        "content": (
            "You are DubaiLocalExplorer, an intelligent assistant that helps tourists explore Dubai. "
            "You engage in natural conversation to understand user preferences, confirm intent, and suggest "
            "personalized day-trip itineraries. Use friendly, concise language. "
            "\n\nYour goal is to:\n"
            "- Help users clarify their interests, budget, group type, and duration\n"
            "- Ask clarifying questions if data is missing\n"
            "- Suggest experiences that match those constraints\n"
            "- Think step-by-step and summarize total cost & time\n\n"
            "Always tailor suggestions based on their profile. Keep the tone warm and adaptive."
        )
    }

    dubai_experiences_examples = [
        {
            "role": "user",
            "content": "Hi! I'm in Dubai for 1 day. I'd love to explore cultural sites and try local food."
        },
        {
            "role": "assistant",
            "content": (
                "That sounds like a wonderful day! Here's a quick plan:\n"
                "1. Start at Al Fahidi Historical District to explore Dubai Museum.\n"
                "2. Ride an abra across the Creek to the Gold and Spice Souks.\n"
                "3. Try Emirati cuisine at Al Seef or Arabian Tea House.\n\n"
                "Would you prefer walking between places, or prefer transport arranged?"
            )
        },
        {
            "role": "user",
            "content": "I'm traveling with my wife, and we have around 700 AED to spend."
        },
        {
            "role": "assistant",
            "content": (
                "Thanks for sharing! That gives us good flexibility.\n"
                "I'll make sure all experiences are within budget for a couple. "
                "Would you like to include modern attractions like Dubai Frame or Museum of the Future?"
            )
        },
        {
            "role": "user",
            "content": "We are a group of friends, want nightlife and beaches, budget is tight though."
        },
        {
            "role": "assistant",
            "content": (
                "Got it — you're a group looking for beach and nightlife fun, but mindful of costs.\n"
                "Let me find beach clubs or night spots with free or low entry fees, and suggest group-friendly spots. "
                "Can you tell me how many days you’re staying?"
            )
        },
        {
            "role": "user",
            "content": "Just one full day. Don’t want to waste time in malls."
        },
        {
            "role": "assistant",
            "content": (
                "Understood — one focused day without shopping distractions.\n"
                "How about this:\n"
                "- Morning: Relax at Kite Beach (free entry, lots of cafés)\n"
                "- Afternoon: Explore JBR beachfront and walk The Beach boardwalk\n"
                "- Evening: Rooftop dinner at a budget-friendly lounge near Dubai Marina\n\n"
                "Want me to include transport suggestions?"
            )
        }
    ]

    return [initial_system_prompt] + dubai_experiences_examples


def get_chat_model_completions(conversation, model="gpt-3.5-turbo", temperature=0.4, tools=None, tool_choice=None, print_response=True):
    """
    Submits a message list (conversation) to the OpenAI ChatCompletion API and supports tool (function) calls.

    Returns:
        dict: {"type": "message" or "tool_call", "content" or "tool_name"/"tool_args"}
    """
    try:
        # Prepare the base request
        request_payload = {
            "model": model,
            "messages": conversation,
            "temperature": temperature,
        }

        # Only add tools and tool_choice if tools are provided
        if tools:
            request_payload["tools"] = tools
            if tool_choice:
                request_payload["tool_choice"] = tool_choice

        # Make the API call
        response = client.chat.completions.create(**request_payload)

        choice = response.choices[0].message

        # Handle tool (function) call
        if hasattr(choice, "tool_calls") and choice.tool_calls:
            tool_call = choice.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            tool_call_id = tool_call.id

            if print_response:
                print(f"\n Assistant wants to call: {tool_name}")
                print("With arguments:", tool_args)

            return {
                "type": "tool_call",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "tool_call_id": tool_call_id
            }

        # Handle plain message
        else:
            message = choice.content.strip()
            if print_response:
                print("\n Assistant Response:\n")
                print(message)

            return {
                "type": "message",
                "content": message
            }

    except Exception as e:
        print("OpenAI API error:", e)


def moderation_check(user_input):
    """
    Uses OpenAI's Moderation API to check if input violates content policy.
    Returns a dict with moderation status and flagged categories.
    """
    try:
        response = client.moderations.create(input=user_input)
        result = response.results[0]

        if result.flagged:
            return f"Flagged by moderation. Categories: {result.categories}"
        
        return "Moderation check passed for given input: "+ user_input

    except Exception as e:
        print("Exception occurred:", e)
        return {
            "flagged": False,
            "categories": {},
            "error": str(e)
        }


def match_experiences_to_profile(user_profile, experiences=dubai_tourist_spots):
    """
    Match Dubai experiences to user profile with scoring and detailed reasoning.

    Args:
        user_profile (dict): Dictionary with keys:
            - interests (list[str])
            - budget_aed (int)
            - duration_days (int)
            - group_type (str)

        experiences (list[dict]): List of Dubai experiences.

    Returns:
        list of dict: Sorted recommended experiences with scores and reasons.
    """

    # Convert list of dicts into DataFrame if needed
    if not isinstance(experiences, pd.DataFrame):
        experiences = pd.DataFrame(experiences)

    # Required columns
    expected = {"name", "tags", "min_budget", "max_budget", 
                "duration_hours", "suitable_for", "description"}
    if not expected.issubset(experiences.columns):
        missing = expected - set(experiences.columns)
        raise KeyError(f"Missing required columns: {missing}")

    # Preprocess columns: lowercase tags & suitable_for lists
    df = experiences.assign(
        tags=experiences["tags"].map(lambda tags: [t.lower().strip() for t in tags]),
        suitable_for=experiences["suitable_for"].map(lambda grp: [g.lower().strip() for g in grp])
    )

    user_interests = set(i.lower().strip() for i in user_profile.get("interests", []))
    budget = user_profile.get("budget_aed", 0)
    group_type = user_profile.get("group_type", "").lower()
    duration_days = float(user_profile.get("duration_days", 0))
    available_hours = duration_days * 8

    def _compute_score(row):
        score = 0
        nodes = []

        # Interest overlap → 10 pts per matched tag (max 40)
        overlap = user_interests.intersection(set(row["tags"]))
        i_score = min(len(overlap) * 10, 40)
        score += i_score
        if overlap:
            nodes.append(f"Interest match: {', '.join(sorted(overlap))} +{i_score}")

        # Budget fit → 30 points if within range, else 0
        if row["min_budget"] <= budget <= row["max_budget"]:
            score += 30
            nodes.append(f"Budget {budget} within [{row['min_budget']}-{row['max_budget']}] +30")
        else:
            nodes.append(f"Budget {budget} outside range +0")

        # Duration check → 20 points if fits
        if row["duration_hours"] <= available_hours:
            score += 20
            nodes.append(f"Duration {row['duration_hours']}h fits in {available_hours}h +20")
        else:
            nodes.append(f"Duration {row['duration_hours']}h too long +0")

        # Group suitability → 10 points if group type matches
        if group_type in row["suitable_for"]:
            score += 10
            nodes.append(f"Group '{group_type}' is suitable +10")
        else:
            nodes.append(f"Group '{group_type}' not a match +0")

        return pd.Series({"score": score, "rationale": "; ".join(nodes)})

    # Apply scoring
    scored = df.apply(_compute_score, axis=1)
    df = df.join(scored)

    # Sort by score desc and return as list of dicts
    df_sorted = df.sort_values(by="score", ascending=False)

    return df_sorted[["name", "description", "score", "rationale"]].to_dict(orient="records")

from typing import List, Dict, Any, Tuple
import json

def product_recommendation_layer(
    scored_recs: List[Dict[str, Any]],
    top_n: int = 3
) -> Tuple[str, str]:
    """
    Select and format top-N recommended experiences for user output.

    Parameters:
      - scored_recs (List[dict]): List of experiences sorted descending by 'score',
        where each dict has keys: 'name', 'description', 'score', 'rationale'.
      - top_n (int): Number of top items to include in the final message.

    Returns:
      - message (str): A polished conversational recommendation prompt.
      - top_recs_json (str): JSON string of top recommendations (for validation).
    """

    if not scored_recs:
        return (
            "Sorry, I couldn't find any experiences that matched your preferences. Could you share more details?",
            json.dumps([])
        )

    top_n = min(top_n, len(scored_recs))

    lines = [
        f"Here are the top {top_n} experiences I recommend:"
    ]

    top_recs = []

    for idx, rec in enumerate(scored_recs[:top_n], start=1):
        lines.append(f"\n{idx}. **{rec['name']}**")
        lines.append(f"   • Description: {rec['description']}")
        lines.append(f"   • Score: {rec['score']} points")
        lines.append(f"   • Why I picked it: {rec['rationale']}")
        
        # Add to output for validation
        top_recs.append({
            "name": rec["name"],
            "description": rec["description"],
            "score": rec["score"],
            "rationale": rec["rationale"]
        })

    lines.append("\nWould you like to book one of these, or explore more options?")

    message = "\n".join(lines)
    return message, json.dumps(top_recs)

import json

def recommendation_validation(top3_recommendations_json):
    try:
        data = json.loads(top3_recommendations_json)
        return [r for r in data if isinstance(r, dict) and r.get("score", 0) > 10]
    except Exception as e:
        print("Validation error:", e)
        return []


## Function Description for the Function Calling API
function_descriptions = [
    {
        "name": "match_experiences_to_profile",
        "description": "Get personalized Dubai experience recommendations based on user's travel interests, budget, available time, and group preferences. Scores and ranks the best-suited experiences.",
        "parameters": {
            "type": "object",
            "properties": {
                "interests": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "User’s top interests while visiting Dubai (e.g., 'culture', 'adventure', 'desert', 'shopping', 'luxury', 'nature'). These will be used to match experience tags."
                },
                "budget_aed": {
                    "type": "integer",
                    "description": "The total budget (in AED) that the user is willing to spend on experiences during their trip."
                },
                "duration_days": {
                    "type": "number",
                    "description": "Total number of days the user will spend in Dubai. Assumes 8 hours of experience time per day."
                },
                "group_type": {
                    "type": "string",
                    "enum": ["solo", "couple", "family", "friends", "group"],
                    "description": "The type of group traveling. Used to filter experiences that are suitable for the travel party."
                },
                "experience_type_preference": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Optional. Categories or types of experiences the user prefers (e.g., 'museums', 'water activities', 'theme parks', 'historical tours'). Helps narrow down the matches further."
                },
                "strict_budget_match": {
                    "type": "boolean",
                    "description": "Optional. If true, only experiences fully within budget are considered. If false or omitted, partial matches are scored but not excluded."
                }
            },
            "required": ["interests", "budget_aed", "duration_days", "group_type"]
        }
    }
]

def format_recommendations(attractions):

    if not attractions:
        return "Sorry, no suitable attractions found."
    
    attractions = json.loads(attractions)
    response = "**Top 3 Dubai Attractions for You:**\n"
    emojis = ["🏜️", "🏖️", "🎢", "🕌", "🛍️", "🌆"]  # fallback emojis

    for i, item in enumerate(attractions):
        name = item.get("name", "Unknown")
        desc = item.get("description", "No description available.")
        emoji = emojis[i % len(emojis)]
        response += f"\n{emoji} **{name}**\n*{desc}*\n"

    return response

def format_recommendations_html(attractions):
    if not attractions:
        return "<p>Sorry, no suitable attractions found.</p>"

    emojis = ["🏜️", "🏖️", "🎢", "🕌", "🛍️", "🌆"]
    response = "<h3>Top 3 Dubai Attractions for You:</h3>"
    
    attractions = json.loads(attractions)
    for i, item in enumerate(attractions):
        name = item.get("name", "Unknown")
        desc = item.get("description", "No description available.")
        emoji = emojis[i % len(emojis)]

        response += f"""
            <div class="attraction-card">
                <h4>{emoji} {name}</h4>
                <p>{desc}</p>
            </div>
        """

    return response


def dialogue_mgmt_system(user_input):
    if user_input.strip() == "" or user_input.strip() == "__start__":
        return (
            "👋 **Welcome to Dubai AI Local Travel Assistant!**\n"
            "I'm your personal AI guide here to help you discover the top attractions, activities, and local experiences in Dubai.\n"
            "Just tell me what you're looking for — and I’ll do the rest! 🏝️🌆🐪"
        )
    user_conversation = initialize_conversation()

    user_conversation.append({"role": "user", "content": user_input})

    moderation = moderation_check(user_input)
    if 'Flagged' in moderation:
        return "Sorry, this message has been flagged. Please restart your conversation."
    
    

    response_from_assistant = get_chat_model_completions(
                                        user_conversation,
                                        model="gpt-3.5-turbo",
                                        temperature=0.4,
                                        tools=[{"type": "function", "function": f} for f in function_descriptions],
                                        tool_choice="auto"
                                    )

    try:  
        if response_from_assistant["type"] == "tool_call":
            print("\nThank you for providing all the information. Kindly wait, while I fetch the details \n")
            
            # Step 2: Extract top3 Dubai Local attractions by calling the external function
            function_name  = response_from_assistant["tool_name"]
            function_args  = response_from_assistant["tool_args"]
            print(f"User requirement: {function_args }")
            recommendations = match_experiences_to_profile(function_args)
            print("scores: \n",recommendations[0])
            top3_recommendations, scores_dict = product_recommendation_layer(recommendations)
            print("Top3 attractions: \n",top3_recommendations)
            assistant_response = format_recommendations_html(scores_dict)
            function_response = recommendation_validation(scores_dict)
            if not function_response:
                return "Sorry, no matching attractions. Connecting you to a human expert."

            return assistant_response

        else:
            return response_from_assistant["content"]

    except Exception as e:
        return f"Error processing request: {str(e)}"
                 