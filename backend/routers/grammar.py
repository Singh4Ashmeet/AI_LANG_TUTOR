from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_user
from ..models.user import User
from ..services.agents import call_lesson_architect

router = APIRouter(prefix="/grammar", tags=["grammar"])

_grammar_cache: dict[str, dict] = {}


def _pair(user: User) -> str:
    return f"{user.native_language or 'en'}-{user.target_language or 'es'}"


def _fallback_guide(user: User) -> dict:
    language = user.target_language or "spanish"
    return {
        "title": f"{language.title()} Grammar Guide",
        "sections": [
            {
                "category": "Verb tenses",
                "rules": [
                    {
                        "rule": "Present tense basics",
                        "explanation": "Use the present tense for habits, identity, and things happening now.",
                        "examples": [
                            {"target": "Yo estudio cada dia.", "native": "I study every day."},
                            {"target": "Ella trabaja aqui.", "native": "She works here."},
                            {"target": "Vivimos en una ciudad pequena.", "native": "We live in a small city."},
                            {"target": "Como pan por la manana.", "native": "I eat bread in the morning."},
                            {"target": "Aprenden rapido.", "native": "They learn quickly."},
                        ],
                    }
                ],
            },
            {
                "category": "Pronouns",
                "rules": [
                    {
                        "rule": "Subject pronouns",
                        "explanation": "Subject pronouns show who is doing the action and help you choose the right verb form.",
                        "examples": [
                            {"target": "Yo soy estudiante.", "native": "I am a student."},
                            {"target": "Tu eres amable.", "native": "You are kind."},
                            {"target": "El vive en Madrid.", "native": "He lives in Madrid."},
                            {"target": "Nosotros hablamos mucho.", "native": "We speak a lot."},
                            {"target": "Ellos comen juntos.", "native": "They eat together."},
                        ],
                    }
                ],
            },
            {
                "category": "Adjectives",
                "rules": [
                    {
                        "rule": "Adjective agreement",
                        "explanation": "Adjectives often match the noun in gender and number.",
                        "examples": [
                            {"target": "Una casa bonita.", "native": "A pretty house."},
                            {"target": "Dos libros nuevos.", "native": "Two new books."},
                            {"target": "Un chico alto.", "native": "A tall boy."},
                            {"target": "Las mesas rojas.", "native": "The red tables."},
                            {"target": "Una idea interesante.", "native": "An interesting idea."},
                        ],
                    }
                ],
            },
            {
                "category": "Sentence structure",
                "rules": [
                    {
                        "rule": "Basic word order",
                        "explanation": "Start with subject + verb + object before trying more flexible structures.",
                        "examples": [
                            {"target": "Yo leo un libro.", "native": "I read a book."},
                            {"target": "Maria prepara la cena.", "native": "Maria prepares dinner."},
                            {"target": "Ellos visitan el museo.", "native": "They visit the museum."},
                            {"target": "Nosotros vemos una pelicula.", "native": "We watch a movie."},
                            {"target": "Tu escribes una carta.", "native": "You write a letter."},
                        ],
                    }
                ],
            },
        ],
    }


@router.get("/guide")
async def grammar_guide(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    pair = _pair(user)
    if pair in _grammar_cache:
        return _grammar_cache[pair]
    
    user_dict = user.model_dump()
    prompt = {
        "role": "user",
        "content": (
            "Generate a complete grammar guide JSON organized by: Verb tenses, Pronouns, Adjectives, Sentence structure. "
            "Each rule should include explanation and 5 examples. Return JSON only."
        ),
    }
    result = await call_lesson_architect([prompt], user_dict)
    if not isinstance(result, dict):
        result = _fallback_guide(user)
    if "sections" not in result:
        result = _fallback_guide(user)
    _grammar_cache[pair] = result
    return result


@router.post("/deep-dive/{rule}")
async def deep_dive(rule: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    user_dict = user.model_dump()
    prompt = {
        "role": "user",
        "content": (
            "Generate 5 targeted exercises for this grammar rule. Return JSON: {rule, exercises:[{type, prompt, content, choices, correct_answer, explanation}]} "
            f"Rule: {rule}."
        ),
    }
    result = await call_lesson_architect([prompt], user_dict)
    if not isinstance(result, dict):
        result = {
            "rule": rule,
            "exercises": [
                {
                    "type": "fill_blank",
                    "prompt": f"Complete the sentence for {rule}",
                    "content": "Yo ___ estudiante.",
                    "choices": ["soy", "es", "somos"],
                    "correct_answer": "soy",
                    "explanation": "Use soy with yo.",
                },
                {
                    "type": "translation",
                    "prompt": f"Practice {rule}",
                    "content": "I am tired.",
                    "correct_answer": "Estoy cansado",
                    "explanation": "Use estar for temporary states.",
                },
                {
                    "type": "multiple_choice",
                    "prompt": "Pick the best answer",
                    "content": "Choose the correct form",
                    "choices": ["eres", "soy", "somos"],
                    "correct_answer": "soy",
                    "explanation": "Match the verb to the subject.",
                },
                {
                    "type": "sentence_build",
                    "prompt": "Build the sentence",
                    "content": "yo / feliz / estoy",
                    "correct_answer": "Yo estoy feliz",
                    "explanation": "Put the subject before the verb in simple sentences.",
                },
                {
                    "type": "explain",
                    "prompt": "Why is this correct?",
                    "content": "Ella es profesora.",
                    "correct_answer": "Uses ser for identity.",
                    "explanation": "Ser is used for identity or profession.",
                },
            ],
        }
    return result
