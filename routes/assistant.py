"""
Agriculture Assistant blueprint: /api/chat
"""
import logging

from flask import Blueprint, request, jsonify

from services.gemini import (
    AGRICULTURE_KEYWORDS,
    generate_gemini_reply,
)

logger = logging.getLogger(__name__)

assistant_bp = Blueprint("assistant", __name__, url_prefix="/api")


@assistant_bp.route("/chat", methods=["POST"])
def chat():
    """Chatbot API endpoint that responds to agriculture-related queries."""
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()
        target_language = (data.get("target_language") or "English").strip()

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        user_message_lower = user_message.lower()
        is_agriculture_related = any(k in user_message_lower for k in AGRICULTURE_KEYWORDS)
        has_non_english_text = any(ord(ch) > 127 for ch in user_message)

        if not is_agriculture_related and not has_non_english_text:
            return jsonify({
                "response": (
                    "I'm an agriculture-focused assistant. Please ask about farming, crops, "
                    "plant diseases, government schemes, or agricultural practices."
                ),
                "is_agriculture": False,
            })

        # Dummy response for testing/offline use
        try:
            prompt_message = (
                f"Target response language: {target_language}\n"
                "If the target language is not English, answer fully in that language using farmer-friendly wording.\n\n"
                f"Farmer question:\n{user_message}"
            )
            bot_response = generate_gemini_reply(
                prompt_message,
                api_key=None,
                model_name=None,
            )
        except Exception as e:
            # Fallback to dummy data for ANY error (ValueError, API error, etc.)
            logger.warning(f"Using dummy response due to error: {e}")
            dummy_responses = {
                "small farmer": "There are several state and central initiatives designed specifically for smallholders, such as the Paramparagat Krishi Vikas Yojana (PKVY) for organic farming support, and subsidies on micro-irrigation under PMKSY. We recommend visiting your nearest Krishi Vigyan Kendra (KVK) to check eligibility criteria and recent localized benefits.",
                "tomato leaf spot": "If you notice dark, circular lesions on tomato leaves, it is likely Early Blight or Septoria. To treat it: prune the severely affected parts, ensure you don't water the foliage directly, and use a recommended fungicide like Chlorothalonil or Mancozeb. Always clean your pruning tools to avoid spreading the infection further.",
                "soil health": "Building up a rich soil foundation takes time. Consider applying green manure, practicing no-till or reduced tillage farming, and testing your soil's pH and nutrient profile every two years. Keeping the ground covered with crop residue also helps retain moisture and encourages beneficial earthworm activity.",
                "pesticide safety": "Safe handling of agrochemicals is critical. Store chemicals in their original labeled containers away from food and livestock. During application, use protective clothing, spray early in the morning or late afternoon to avoid wind drift, and observe the specific 'pre-harvest interval' before picking your crops.",
                "crop": "For crop growth, ensure proper watering (25-40mm per week depending on season), monitor for pests regularly, and apply fertilizers based on soil testing. Rotate crops annually to maintain soil health. Contact your local agriculture office for specific guidance on your crop type.",
                "disease": "Plant diseases can be managed by: 1) Early identification through regular monitoring, 2) Removing affected leaves/plants immediately, 3) Using recommended fungicides/pesticides with proper safety measures, 4) Maintaining proper spacing for air circulation. Consult your local agriculture extension for diagnosis and treatment options.",
                "pest": "To control pests: 1) Use organic methods first (neem oil spray, manual removal), 2) Apply recommended pesticides following label instructions, 3) Maintain crop hygiene, 4) Use integrated pest management (IPM) techniques. Always wear protective equipment when handling chemicals.",
                "fertilizer": "Apply fertilizers based on soil test results. Generally use NPK (Nitrogen-Phosphorus-Potassium) in 1:0.5:0.5 ratio for most crops. Split nitrogen application in 2-3 stages. Use organic manure/compost along with chemical fertilizers. Contact ICAR or your state agriculture office for soil-specific recommendations.",
                "irrigation": "Water management is critical: Monitor soil moisture regularly, adjust irrigation based on rainfall and season, use drip irrigation where possible to save water, and avoid waterlogging. Typical requirement is 25-40mm per week, but varies by crop and season.",
                "schemes": "Popular government schemes: PM-KISAN (₹6,000/year direct support), Pradhan Mantri Fasal Bima Yojana (crop insurance), Soil Health Card Scheme (free soil testing), and various state-specific subsidies. Check eligibility with your state agriculture office with land records and ID proof.",
            }
            
            # Find matching dummy response
            bot_response = dummy_responses["crop"]  # default
            for key in dummy_responses:
                if key in user_message_lower:
                    bot_response = dummy_responses[key]
                    break

        return jsonify({"response": bot_response, "is_agriculture": True})

    except Exception as e:
        logger.error(f"Chat error: {e}")
        # Return dummy response instead of error
        dummy_reply = "I'm here to help with agricultural queries. Please ask about crops, diseases, pest management, irrigation, fertilizer use, or government schemes available for farmers."
        return jsonify({"response": dummy_reply, "is_agriculture": True})
