"""Configurable LLM provider adapters for Moonscape AI Scientific Explainer."""

from abc import ABC, abstractmethod
import json
import logging
import os
import re
from typing import Any, Dict, Optional

import httpx
from app.core.config import settings

logger = logging.getLogger("moonscape.ai_providers")


class AIProviderError(Exception):
    """Base exception for AI provider errors."""
    pass


class AIAuthenticationError(AIProviderError):
    """Raised when an API key is missing, invalid, or unauthorized."""
    pass


class AIRateLimitError(AIProviderError):
    """Raised when provider rate limits are exceeded."""
    pass


class AITimeoutError(AIProviderError):
    """Raised when the LLM provider fails to respond before timeout."""
    pass


class AIUnavailableError(AIProviderError):
    """Raised when the provider is unreachable or returning 5xx server errors."""
    pass


class BaseAIProvider(ABC):
    """Abstract base class for all AI LLM providers."""

    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: str, timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
        """Sends prompt to the LLM and returns structured JSON output."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has necessary API credentials configured."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the human-readable identifier of the provider."""
        pass


class GeminiProvider(BaseAIProvider):
    """Google Gemini API provider (e.g. gemini-1.5-flash / gemini-2.0-flash)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        self.model = model or getattr(settings, "MOONSCAPE_AI_MODEL", "gemini-1.5-flash")
        self.temperature = temperature if temperature is not None else getattr(settings, "MOONSCAPE_AI_TEMPERATURE", 0.2)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def get_provider_name(self) -> str:
        return f"Google Gemini ({self.model})"

    def generate_json(self, prompt: str, system_prompt: str, timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
        if not self.is_configured():
            raise AIAuthenticationError("GEMINI_API_KEY is not configured in backend environment.")

        timeout = timeout_seconds or getattr(settings, "MOONSCAPE_AI_TIMEOUT_SECONDS", 15.0)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload)

            if response.status_code == 429:
                raise AIRateLimitError("Gemini rate limit exceeded. Development quota exhausted.")
            elif response.status_code in (401, 403):
                raise AIAuthenticationError(f"Gemini API authentication failed: {response.text}")
            elif response.status_code >= 500:
                raise AIUnavailableError(f"Gemini service unavailable (HTTP {response.status_code}).")
            elif response.status_code != 200:
                raise AIProviderError(f"Gemini API returned error HTTP {response.status_code}: {response.text}")

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise AIProviderError("Gemini returned empty candidate list.")

            content_parts = candidates[0].get("content", {}).get("parts", [])
            if not content_parts:
                raise AIProviderError("Gemini returned empty content parts.")

            raw_text = content_parts[0].get("text", "").strip()
            # Clean possible markdown fence wrapping
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            return json.loads(raw_text.strip())

        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"Gemini request timed out after {timeout} seconds.") from exc
        except httpx.RequestError as exc:
            raise AIUnavailableError(f"Failed to connect to Gemini API: {str(exc)}") from exc
        except json.JSONDecodeError as exc:
            raise AIProviderError(f"Failed to parse JSON response from Gemini: {str(exc)}") from exc


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider (e.g. gpt-4o-mini)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        self.model = model or "gpt-4o-mini"
        self.temperature = temperature if temperature is not None else getattr(settings, "MOONSCAPE_AI_TEMPERATURE", 0.2)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def get_provider_name(self) -> str:
        return f"OpenAI ({self.model})"

    def generate_json(self, prompt: str, system_prompt: str, timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
        if not self.is_configured():
            raise AIAuthenticationError("OPENAI_API_KEY is not configured in backend environment.")

        timeout = timeout_seconds or getattr(settings, "MOONSCAPE_AI_TIMEOUT_SECONDS", 15.0)
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": self.temperature,
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code == 429:
                raise AIRateLimitError("OpenAI rate limit exceeded.")
            elif response.status_code in (401, 403):
                raise AIAuthenticationError(f"OpenAI authentication failed: {response.text}")
            elif response.status_code >= 500:
                raise AIUnavailableError(f"OpenAI service unavailable (HTTP {response.status_code}).")
            elif response.status_code != 200:
                raise AIProviderError(f"OpenAI API returned HTTP {response.status_code}: {response.text}")

            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            return json.loads(raw_text.strip())

        except httpx.TimeoutException as exc:
            raise AITimeoutError(f"OpenAI request timed out after {timeout} seconds.") from exc
        except httpx.RequestError as exc:
            raise AIUnavailableError(f"Failed to connect to OpenAI API: {str(exc)}") from exc
        except json.JSONDecodeError as exc:
            raise AIProviderError(f"Failed to parse JSON response from OpenAI: {str(exc)}") from exc


class MockDeterministicProvider(BaseAIProvider):
    """Rule-grounded deterministic explainer that requires no external network or API keys."""

    def __init__(self, model_name: str = "Deterministic Scientific Rule Engine v1.0") -> None:
        self.model_name = model_name

    def is_configured(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return self.model_name

    def generate_json(self, prompt: str, system_prompt: str, timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
        """Synthesizes structured scientific insights from measurements embedded in the prompt."""
        # Extract measurements from prompt text via simple regex/parsing
        def safe_extract_float(pattern: str, text: str) -> Optional[float]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    return None
            return None

        mean_slope = safe_extract_float(r"Mean slope:\s*([\d\.]+)\s*deg", prompt)
        roughness = safe_extract_float(r"RMS roughness:\s*([\d\.]+)\s*m", prompt)
        illum = safe_extract_float(r"illumination:\s*([\d\.]+)\s*%", prompt)
        elevation = safe_extract_float(r"Mean elevation:\s*(-?[\d\.]+)\s*m", prompt)
        overall_score = safe_extract_float(r"Overall score:\s*([\d\.]+)", prompt)

        positive_factors = []
        risk_factors = []
        limitations = []

        # Analyze Slope
        if mean_slope is not None:
            if mean_slope <= 5.0:
                positive_factors.append(f"Benign local slope averaging {mean_slope:.1f}° falls well below the 8° Artemis threshold, significantly reducing lander tip-over risk.")
            elif mean_slope <= 8.0:
                positive_factors.append(f"Mean slope of {mean_slope:.1f}° is within acceptable nominal landing gear stability tolerances.")
            elif mean_slope <= 15.0:
                risk_factors.append(f"Elevated average slope of {mean_slope:.1f}° approaches critical Apollo tipping limits (12°-15°), requiring terrain-relative navigation.")
            else:
                risk_factors.append(f"Severe regional slope ({mean_slope:.1f}°) exceeds safe landing gear limits (> 15°), presenting catastrophic tip-over danger.")
        else:
            limitations.append("Topographic slope data is missing or unmeasured. Slope is the primary touchdown safety factor.")

        # Analyze Roughness
        if roughness is not None:
            if roughness <= 0.20:
                positive_factors.append(f"Micro-topographic RMS roughness of {roughness:.2f}m indicates relatively smooth, uniform regolith suitable for footpad contact.")
            elif roughness <= 0.50:
                positive_factors.append(f"Surface roughness of {roughness:.2f}m is within nominal operational range for robotic and crewed landing gear.")
            else:
                risk_factors.append(f"High surface roughness ({roughness:.2f}m RMS) suggests boulder fields or micro-craters that could breach belly-pan clearance.")

        # Analyze Illumination
        if illum is not None:
            if illum >= 70.0:
                positive_factors.append(f"Strong solar illumination ({illum:.1f}%) provides reliable photovoltaic array power and mitigates severe cryogenic cooling.")
            elif illum >= 40.0:
                risk_factors.append(f"Moderate cumulative illumination ({illum:.1f}%) requires careful landing window timing to avoid prolonged shadow cycles.")
            else:
                risk_factors.append(f"Low illumination ({illum:.1f}%) indicates proximity to deep cold traps, requiring supplemental fuel cells or nuclear power.")

        # Analyze Elevation
        if elevation is not None:
            if elevation > 0:
                positive_factors.append(f"Elevated topographic relief ({elevation:.0f}m above datum) enhances line-of-sight to Earth ground stations and the Sun.")
            else:
                risk_factors.append(f"Depressed elevation ({elevation:.0f}m relative to datum) may experience intermittent horizon occultation by surrounding crater rims.")

        # Ensure comprehensive balanced assessment
        if len(positive_factors) < 2:
            positive_factors.append("Regional topography features landing corridors with manageable tilt envelopes for terminal descent.")
        if len(risk_factors) < 2:
            risk_factors.append("Low grazing solar angles (< 2°) produce dynamic, elongated shadows that complicate optical navigation.")
        if len(risk_factors) < 2:
            risk_factors.append("Sub-pixel boulder fields require terminal hazard detection and avoidance (HDA) maneuvers.")

        # Limitations & Caveats
        limitations.append("Analysis is a preliminary computational screening indicator and does NOT constitute NASA-certified flight clearance.")
        if "Crater Hazards" in prompt or "missing" in prompt.lower():
            limitations.append("High-resolution optical crater and boulder hazard counts are uncalibrated or pending orbital ground-truth validation.")

        # Extract user query if present
        query_match = re.search(r"SPECIFIC USER INQUIRY:\s*(.+)", prompt, re.IGNORECASE)
        user_query = query_match.group(1).strip() if query_match else ""

        # Default general synthesis
        explanation = (
            f"Preliminary scientific screening of candidate landing coordinates indicates an evaluated suitability score of "
            f"{overall_score if overall_score is not None else 'N/A'}/100. "
            f"The site's primary operational advantage is {'its benign slope profile' if mean_slope and mean_slope <= 8.0 else 'its solar availability'}, "
            f"while mission planners must account for {'micro-topographic relief' if roughness and roughness > 0.3 else 'elongated polar shadowing'}."
        )

        # Grounded Answers to Specific Scientific Inquiries
        q_lower = user_query.lower()
        if "hazard" in q_lower:
            slope_txt = f"{mean_slope:.1f}°" if mean_slope is not None else "unmeasured"
            rough_txt = f"{roughness:.2f}m RMS" if roughness is not None else "unmeasured"
            explanation = (
                f"Physical hazards evaluated at this location include: (1) Topographic slope averaging {slope_txt} "
                f"(critical stability limit >15.0° triggers dynamic tip-over risk), (2) Surface micro-roughness of {rough_txt} "
                f"which impacts lander footpad differential height and engine nozzle ground clearance, (3) Polar shadowing "
                f"with {illum if illum is not None else 'unmeasured'}% cumulative sunlight creating deep thermal sinks, and "
                f"(4) Sub-pixel boulder hazards smaller than LOLA's 20m spatial resolution requiring terminal lidar sensing."
            )
        elif "earth" in q_lower or "visible" in q_lower or "comm" in q_lower or "blackout" in q_lower:
            explanation = (
                "Direct line-of-sight communication to Earth from lunar polar latitudes is governed by lunar orbital libration "
                "(which produces an apparent ±8° wobble of Earth in the lunar sky) and local terrain horizon occlusion. "
                "When Earth's elevation angle dips below the elevation angle of surrounding crater rims or highland massifs, "
                "direct radio line-of-sight is blocked. These periodic blackout windows require scheduling direct downlink "
                "during peak positive libration or relaying through orbital communication spacecraft (e.g. Lunar Gateway)."
            )
        elif "month" in q_lower or "later" in q_lower or "season" in q_lower or "time" in q_lower:
            explanation = (
                "A mission start shifted by one month alters solar illumination geometry through the Moon's 18.6-year draconic "
                "precession cycle and seasonal sub-solar latitude variations (ranging ±1.54°). Because the Sun grazes the lunar South "
                "Pole at angles typically between 0.5° and 1.5° above the horizon, even a 0.5° seasonal variation changes shadow lengths "
                "by hundreds of meters, altering continuous sunlight duration, battery sizing margins, and local surface temperatures."
            )
        elif "uncertain" in q_lower:
            explanation = (
                "Primary measurement uncertainties at this site include: (1) LOLA laser altimeter vertical accuracy standard error "
                "of approximately ±1.5 m, (2) Topographic gradient uncertainty of ±1.2° resulting from track interpolation across 10-25m "
                "laser shot baselines, (3) Surface roughness estimates constrained by regional Nyquist frequencies, and (4) Secondary "
                "radiative scattering uncertainties in deep crater cold traps where temperatures drop to 40 K."
            )
        elif "additional" in q_lower or "improve" in q_lower or "data" in q_lower or "validate" in q_lower:
            explanation = (
                "To advance this candidate beyond preliminary computational screening toward flight landing clearance, the following "
                "measurements are required: (1) Targeted LROC Narrow Angle Camera (NAC) stereo photogrammetric DTMs at 0.5m to 2.0m resolution "
                "to resolve meter-scale rocks and rim slopes, (2) Diviner multi-channel infrared radiometer thermal emission observations "
                "to map surface regolith thermal inertia, and (3) Mini-RF bistatic radar backscatter measurements to assess subsurface "
                "dielectric constants and potential volatile ice deposits."
            )
        elif "rank" in q_lower or "compare" in q_lower or "above" in q_lower or "why is" in q_lower:
            explanation = (
                f"Candidate site ranking is governed by multi-criteria decision analysis prioritizing topographic landing safety "
                f"(slopes and roughness account for 50-55% of the total weight) alongside solar illumination availability (20-25%). "
                f"A site ranked higher exhibits gentler mean slopes (< 5°), lower RMS surface roughness, and a larger contiguous "
                f"touchdown footprint (>= 100m diameter for Artemis HLS), directly minimizing static and dynamic tip-over hazards."
            )

        return {
            "explanation": explanation,
            "positive_factors": positive_factors or ["Terrain data available for preliminary computational screening."],
            "risk_factors": risk_factors or ["Surface micro-relief requires final descent hazard avoidance."],
            "limitations": limitations,
            "conclusion": "Preliminary assessment only. Candidate site warrants high-resolution LROC photogrammetric validation.",
        }


def get_ai_provider(provider_type: Optional[str] = None) -> BaseAIProvider:
    """Factory creating the appropriate AI provider based on configuration and available keys."""
    requested = (provider_type or getattr(settings, "MOONSCAPE_AI_PROVIDER", "auto")).strip().lower()

    if requested == "gemini":
        return GeminiProvider()
    elif requested == "openai":
        return OpenAIProvider()
    elif requested == "mock":
        return MockDeterministicProvider()
    elif requested == "auto":
        # Check if Gemini key is available
        gemini = GeminiProvider()
        if gemini.is_configured():
            logger.info("Auto-selected Google Gemini provider for AI Explainer.")
            return gemini

        # Check if OpenAI key is available
        openai = OpenAIProvider()
        if openai.is_configured():
            logger.info("Auto-selected OpenAI provider for AI Explainer.")
            return openai

        # Default to offline deterministic provider
        logger.info("No external LLM API key detected. Defaulting to offline deterministic rule provider.")
        return MockDeterministicProvider()

    # Fallback
    logger.warning(f"Unknown AI provider '{requested}'. Defaulting to MockDeterministicProvider.")
    return MockDeterministicProvider()
