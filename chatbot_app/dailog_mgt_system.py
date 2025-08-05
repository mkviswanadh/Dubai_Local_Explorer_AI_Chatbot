from chatbot import initialize_conversation, get_chat_model_completions, moderation_check, intent_confirmation_layer, dictionary_present, product_mapping, \
    extract_information, match_experiences_to_profile, product_recommendation_layer, extract_dictionary_from_string

def clarify_prompt(missing_keys):
    prompts = []
    if "interests" in missing_keys:
        prompts.append("What types of experiences interest you? (e.g., culture, beach, food)")
    if "budget_aed" in missing_keys:
        prompts.append("What is your budget in AED?")
    if "duration_days" in missing_keys:
        prompts.append("How many days will you spend in Dubai?")
    if "group_type" in missing_keys:
        prompts.append("Are you traveling alone, as a couple, with family, or friends?")
    return "I just need a few more details: " + " ".join(prompts)


class DialogueManagementSystem:
    def __init__(self):
        self.state = "INIT"
        self.profile = {}
        self.last_recommendations = []


    def dialogue_mgmt_system(self, user_msg: str) -> str:
        # Step 1: Moderate unsafe content
        if "Flagged by moderation" in moderation_check(user_msg):
            return "Sorry, that message isn't allowed. Please let us valid message."

        # Step 2: INIT state
        if self.state == "INIT":
            user_conversation = initialize_conversation()
            response_from_assistant = get_chat_model_completions(user_conversation)
            confirmation = intent_confirmation_layer(response_from_assistant)
            # Step 2a: Check if user already gave dictionary-like info
            if confirmation:
                profile_dict = extract_information(response_from_assistant)
                #profile_dict = dictionary_present(response_from_assistant)
                self.profile = profile_dict
                self.state = "PROFILE_CONFIRMED"
                recommended = product_mapping(profile_dict)
                recommendations_with_scores = match_experiences_to_profile(profile_dict)
                top3_recommendations = product_recommendation_layer(recommendations_with_scores)
                self.last_recommendations = top3_recommendations
                #return greeting + "\n\n" + confirmation + "\n" + product_recommendation_layer(recs)
                return top3_recommendations

            # Step 2b: Extract from free-form input
            info = extract_information(user_msg)
            if not info or info.get("missing_info"):
                self.profile = info
                self.state = "PROFILE_COLLECTING"
                return greeting + "\n\n" + clarify_prompt(info.get("missing_info", []))

            self.profile = info
            self.state = "PROFILE_CONFIRMED"
            confirmation = intent_confirmation_layer(self.profile)
            product_mapping_layer(self.profile)
            recs = match_experiences_to_profile(self.profile)
            self.last_recommendations = recs
            return greeting + "\n\n" + confirmation + "\n" + product_recommendation_layer(recs)

        # Step 3: Fill missing info
        elif self.state == "PROFILE_COLLECTING":
            info = extract_information(user_msg)
            if info:
                self.profile.update({k: v for k, v in info.items() if v is not None})

            if self.profile.get("missing_info"):
                return clarify_prompt(self.profile["missing_info"])

            self.state = "PROFILE_CONFIRMED"
            confirmation = intent_confirmation_layer(self.profile)
            product_mapping_layer(self.profile)
            recs = match_experiences_to_profile(self.profile)
            self.last_recommendations = recs
            return confirmation + "\n" + product_recommendation_layer(recs)

        # Step 4: After confirmation, allow booking or changes
        elif self.state == "PROFILE_CONFIRMED":
            msg = user_msg.lower()
            if "book" in msg or "reserve" in msg:
                self.state = "BOOKING_REQUEST"
                return "Great! Which experience would you like to book? Type the exact name."
            if "change" in msg or "update" in msg:
                self.state = "PROFILE_COLLECTING"
                self.profile["missing_info"] = ["interests", "budget_aed", "duration_days", "group_type"]
                return "Sure, what would you like to change?"

            return "Would you like to book one of these, or update your preferences?"

        # Step 5: Booking
        elif self.state == "BOOKING_REQUEST":
            selected = user_msg.lower()
            matched = next((e for e in self.last_recommendations if e["experience"].lower() == selected), None)
            if matched:
                self.state = "BOOKING_CONFIRMED"
                return f"Booking confirmed for **{matched['experience']}**! Have an amazing experience."
            return "Couldn't find that experience in your list. Please copy the name exactly."

        # Step 6: Booking confirmed
        elif self.state == "BOOKING_CONFIRMED":
            self.state = "INIT"
            self.profile = {}
            return "Booking successful. Would you like to plan something else?"

        # Fallback
        else:
            self.state = "INIT"
            return "Something went wrong. Let's start over. Tell me your preferences!"
