"""Conservative text checks; these do not verify facts or Hindi grammar."""

import re
import unicodedata


HINDI_INSTRUCTION = (
    "Reply in natural, grammatically correct Hindi using Devanagari. "
    "Answer the latest question directly; use one short sentence for a simple fact. "
    "Use previous turns only when relevant to this question. Do not invent facts or definitions. "
    "If unsure, say you do not know; if the question is unclear, ask for clarification. "
    "Names, numbers and technical terms may retain their original spelling. "
    "Follow an explicit request for translation or another response language. "
    "सरल और स्वाभाविक हिंदी में उत्तर दें। अनुमान लगाकर तथ्य न बनाएं।"
)


def normalize_text(text: str) -> str:
    """Keep letters, vowel marks, names and punctuation; never guess corrections."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def text_quality_error(text: str) -> str | None:
    if not text.strip():
        return "empty text"
    if "\ufffd" in text or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
        return "malformed text"
    if any(marker in text for marker in ("<|im_start|>", "<|im_end|>", "<tool_call>")):
        return "model control tokens"
    words = [word.casefold().strip(".,!?।॥:;") for word in text.split()]
    # Four consecutive repeats of a word/short phrase are a clear decoding loop.
    for width in range(1, 5):
        for start in range(len(words) - width * 4 + 1):
            phrase = words[start:start + width]
            if any(phrase) and words[start:start + width * 4] == phrase * 4:
                return "repeated phrase loop"
    return None
