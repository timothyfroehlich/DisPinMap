"""
LLM-based Semantic Assertions for Discord Bot Testing

This module provides semantic validation of bot responses using an LLM,
making tests resilient to message format changes while ensuring responses
are meaningful and appropriate.
"""

import json
import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


class LLMAssertions:
    """Provides LLM-based semantic assertions for bot testing."""

    def __init__(self):
        self.validation_cache = {}  # Cache for repeated validations

    def assert_response_indicates_success(
        self, messages: List[str], action_description: str
    ) -> bool:
        """
        Assert that the bot's response indicates the action was successful.

        Args:
            messages: List of bot response messages
            action_description: Description of what action was attempted (e.g., "adding location monitoring")

        Returns:
            bool: True if response indicates success
        """
        prompt = f"""
        A Discord bot was asked to perform this action: {action_description}

        The bot responded with these messages:
        {json.dumps(messages, indent=2)}

        Analyze these messages and determine:
        1. Does the response indicate the action was SUCCESSFUL?
        2. Are the messages appropriate and helpful for a user?
        3. Do the messages provide useful information related to the action?

        Respond with JSON:
        {{
            "success": true/false,
            "explanation": "brief explanation of why this indicates success or failure",
            "appropriate": true/false,
            "feedback": "any issues with the response quality"
        }}

        Consider successful responses to include:
        - Explicit success confirmations (✅ messages)
        - Showing relevant data (like recent submissions for a location)
        - Helpful information that indicates the action worked

        Consider failure responses to include:
        - Error messages (❌ messages)
        - "Not found" or "Invalid" messages
        - Empty/no response
        - Confusing or unhelpful responses
        """

        return self._evaluate_with_llm(
            prompt, messages, f"success:{action_description}"
        )

    def assert_response_indicates_error(
        self, messages: List[str], expected_error_type: str
    ) -> bool:
        """
        Assert that the bot's response appropriately indicates an error.

        Args:
            messages: List of bot response messages
            expected_error_type: Type of error expected (e.g., "location not found", "invalid coordinates")

        Returns:
            bool: True if response appropriately indicates the expected error
        """
        prompt = f"""
        A Discord bot was expected to return an error of type: {expected_error_type}

        The bot responded with these messages:
        {json.dumps(messages, indent=2)}

        Analyze these messages and determine:
        1. Does the response indicate an ERROR occurred?
        2. Is the error message clear and helpful to the user?
        3. Does the error type match what was expected: {expected_error_type}?

        Respond with JSON:
        {{
            "is_error": true/false,
            "appropriate_error": true/false,
            "explanation": "brief explanation of the error indication",
            "helpful": true/false,
            "feedback": "any issues with the error message quality"
        }}

        Good error responses include:
        - Clear ❌ error messages
        - Specific explanations of what went wrong
        - Suggestions for how to fix the issue
        - Appropriate error type for the situation
        """

        return self._evaluate_with_llm(prompt, messages, f"error:{expected_error_type}")

    def assert_response_provides_information(
        self, messages: List[str], information_type: str
    ) -> bool:
        """
        Assert that the bot's response provides the expected type of information.

        Args:
            messages: List of bot response messages
            information_type: Type of information expected (e.g., "list of monitoring targets", "recent submissions")

        Returns:
            bool: True if response provides the expected information
        """
        prompt = f"""
        A Discord bot was expected to provide information of type: {information_type}

        The bot responded with these messages:
        {json.dumps(messages, indent=2)}

        Analyze these messages and determine:
        1. Does the response provide the expected type of information?
        2. Is the information presented clearly and usefully?
        3. Would a user understand what this information means?

        Respond with JSON:
        {{
            "provides_info": true/false,
            "correct_type": true/false,
            "explanation": "brief explanation of what information is provided",
            "clear": true/false,
            "feedback": "any issues with the information presentation"
        }}

        Expected information type: {information_type}
        """

        return self._evaluate_with_llm(prompt, messages, f"info:{information_type}")

    def assert_response_quality(
        self, messages: List[str], context: str
    ) -> Dict[str, Any]:
        """
        Perform a general quality assessment of bot responses.

        Args:
            messages: List of bot response messages
            context: Context about what the bot was doing

        Returns:
            Dict with quality assessment results
        """
        prompt = f"""
        A Discord bot responded in this context: {context}

        The bot's response messages:
        {json.dumps(messages, indent=2)}

        Evaluate the overall quality of this response:
        1. Is it helpful and informative?
        2. Is it appropriately formatted for Discord?
        3. Does it use appropriate emojis and formatting?
        4. Is the tone appropriate for a bot?
        5. Are there any obvious issues?

        Respond with JSON:
        {{
            "helpful": true/false,
            "well_formatted": true/false,
            "appropriate_tone": true/false,
            "uses_discord_features": true/false,
            "overall_score": 1-10,
            "strengths": ["list", "of", "strengths"],
            "improvements": ["list", "of", "suggested", "improvements"]
        }}
        """

        result = self._evaluate_with_llm(prompt, messages, f"quality: {context}")
        return (
            result
            if isinstance(result, dict)
            else {"error": "Failed to evaluate quality"}
        )

    def _evaluate_with_llm(
        self, prompt: str, messages: List[str], cache_key: str
    ) -> Any:
        """
        Send prompt to Gemini API and parse response.

        Args:
            prompt: The prompt to send to the LLM
            messages: The messages being evaluated (for caching)
            cache_key: Key for caching results

        Returns:
            Parsed JSON response from LLM
        """
        # Create cache key from messages and cache_key
        full_cache_key = f"{cache_key}:{hash(str(messages))}"

        if full_cache_key in self.validation_cache:
            return self.validation_cache[full_cache_key]

        try:
            result = self._call_gemini_api(prompt)
            self.validation_cache[full_cache_key] = result
            return result

        except Exception as e:
            logger.warning(
                f"Gemini API evaluation failed: {e}, falling back to heuristics"
            )
            # Fallback to heuristic evaluation
            result = self._heuristic_evaluation(prompt, messages, cache_key)
            self.validation_cache[full_cache_key] = result
            return result

    def _call_gemini_api(self, prompt: str) -> Any:
        """
        Call the Gemini 2.5 Flash API with the given prompt.

        Args:
            prompt: The prompt to send to Gemini

        Returns:
            Parsed JSON response from Gemini
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # Gemini 2.5 Flash API endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for consistent evaluation
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
            },
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        result = response.json()

        # Extract the text content from Gemini's response format
        if "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                text_content = candidate["content"]["parts"][0]["text"]
                try:
                    # Parse the JSON response
                    return json.loads(text_content)
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse Gemini JSON response: {e}\nResponse: {text_content}"
                    )
                    # Try to extract JSON from the response
                    import re

                    json_match = re.search(r"\{.*\}", text_content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    else:
                        raise ValueError(
                            f"No valid JSON found in Gemini response: {text_content}"
                        )

        raise ValueError(f"Unexpected Gemini API response format: {result}")

    def _heuristic_evaluation(
        self, prompt: str, messages: List[str], cache_key: str
    ) -> Any:
        """
        Fallback heuristic evaluation when LLM is not available.

        Args:
            prompt: The original prompt (for context)
            messages: Messages to evaluate
            cache_key: Type of evaluation being done

        Returns:
            Heuristic evaluation result
        """
        if not messages:
            return {
                "success": False,
                "explanation": "No messages returned",
                "appropriate": False,
                "feedback": "Bot provided no response",
            }

        response_text = " ".join(messages).lower()

        if "success" in cache_key:
            # Success evaluation - only check for actual error indicators, not content words
            has_error = any(
                indicator in response_text
                for indicator in ["❌", "error:", "not found", "invalid", "failed"]
            )
            has_content = len(response_text.strip()) > 10

            # Recognize submission listings as success indicators
            has_submissions = any(
                indicator in response_text
                for indicator in ["submissions", "🎮", "🗑️", "added at", "removed from"]
            )
            has_location_name = any(
                name in response_text for name in ["seattle pinball museum", "location"]
            )

            # Success if: no errors AND (has content OR shows submissions/activity)
            success = (
                not has_error
                and (has_content or has_submissions)
                and not (
                    "0 submissions" in response_text
                    or "no submissions" in response_text
                )
            )

            explanation = []
            if has_error:
                explanation.append("Error indicators found")
            if has_submissions:
                explanation.append("Shows submission activity")
            if has_location_name:
                explanation.append("Contains expected location")
            if not has_content:
                explanation.append("No content")

            return {
                "success": success,
                "explanation": f"Heuristic: {', '.join(explanation) if explanation else 'Basic content check'}",
                "appropriate": has_content or has_submissions,
                "feedback": "Heuristic evaluation - LLM not available",
            }

        elif cache_key.startswith("info:"):
            # Information evaluation
            has_error = any(
                indicator in response_text
                for indicator in ["❌", "error:", "not found", "invalid", "failed"]
            )
            has_content = len(response_text.strip()) > 10

            # Recognize submission listings as information
            has_submissions = any(
                indicator in response_text
                for indicator in [
                    "submissions",
                    "🎮",
                    "🗑️",
                    "added at",
                    "removed from",
                    "found",
                ]
            )
            has_location_name = any(
                name in response_text for name in ["seattle pinball museum", "location"]
            )

            # Provides info if: no errors AND shows relevant content
            provides_info = not has_error and (
                has_submissions or "submissions" in response_text.lower()
            )

            return {
                "provides_info": provides_info,
                "correct_type": has_submissions,
                "explanation": f"Heuristic: {'Shows submission activity' if has_submissions else 'No submission activity found'}",
                "clear": has_content,
                "feedback": "Heuristic evaluation - LLM not available",
            }

        elif "error" in cache_key:
            # Error evaluation
            has_error = any(
                indicator in response_text
                for indicator in ["❌", "error:", "not found", "invalid", "failed"]
            )

            return {
                "is_error": has_error,
                "appropriate_error": has_error,
                "explanation": f"Heuristic: {'Error indicators found' if has_error else 'No error indicators found'}",
                "helpful": has_error,
                "feedback": "Heuristic evaluation - LLM not available",
            }

        else:
            # General quality evaluation
            has_content = len(response_text.strip()) > 10
            has_emojis = any(
                emoji in response_text for emoji in ["✅", "❌", "🎮", "🗑️", "📍"]
            )

            return {
                "helpful": has_content,
                "well_formatted": has_emojis,
                "appropriate_tone": True,  # Assume good unless we detect issues
                "uses_discord_features": has_emojis,
                "overall_score": 7 if has_content and has_emojis else 4,
                "strengths": ["Has content" if has_content else ""],
                "improvements": ["Add more emojis" if not has_emojis else ""],
            }


# Convenience functions for easy use in tests


def assert_success_response(messages: List[str], action: str) -> None:
    """Assert that messages indicate successful completion of an action."""
    llm = LLMAssertions()
    result = llm.assert_response_indicates_success(messages, action)

    if isinstance(result, dict):
        assert result.get(
            "success", False
        ), f"Response does not indicate success for '{action}': {result.get('explanation', 'No explanation')}\nMessages: {messages}"
        assert result.get(
            "appropriate", False
        ), f"Response is not appropriate for '{action}': {result.get('feedback', 'No feedback')}\nMessages: {messages}"
    else:
        # Fallback: basic success check
        assert len(messages) > 0, f"No response messages for action '{action}'"
        assert not any(
            "❌" in msg for msg in messages
        ), f"Error message found for action '{action}': {messages}"


def assert_error_response(messages: List[str], error_type: str) -> None:
    """Assert that messages appropriately indicate an error."""
    llm = LLMAssertions()
    result = llm.assert_response_indicates_error(messages, error_type)

    if isinstance(result, dict):
        assert result.get(
            "is_error", False
        ), f"Response does not indicate error for '{error_type}': {result.get('explanation', 'No explanation')}\nMessages: {messages}"
        assert result.get(
            "appropriate_error", False
        ), f"Error response is not appropriate for '{error_type}': {result.get('feedback', 'No feedback')}\nMessages: {messages}"
    else:
        # Fallback: basic error check
        assert len(messages) > 0, f"No response messages for error '{error_type}'"
        assert any(
            "❌" in msg for msg in messages
        ), f"No error indicator found for error type '{error_type}': {messages}"


def assert_information_response(messages: List[str], info_type: str) -> None:
    """Assert that messages provide the expected type of information."""
    llm = LLMAssertions()
    result = llm.assert_response_provides_information(messages, info_type)

    if isinstance(result, dict):
        assert result.get(
            "provides_info", False
        ), f"Response does not provide info for '{info_type}': {result.get('explanation', 'No explanation')}\nMessages: {messages}"
        assert result.get(
            "clear", False
        ), f"Information is not clear for '{info_type}': {result.get('feedback', 'No feedback')}\nMessages: {messages}"
    else:
        # Fallback: basic info check
        assert len(messages) > 0, f"No response messages for information '{info_type}'"


def evaluate_response_quality(messages: List[str], context: str) -> Dict[str, Any]:
    """Get a quality assessment of bot responses."""
    llm = LLMAssertions()
    return llm.assert_response_quality(messages, context)
