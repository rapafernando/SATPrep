"""Load skills and questions from a JSON file. Safe to run again: it updates, never duplicates.

    python manage.py seed_content                       # the bundled sample questions
    python manage.py seed_content --file my_items.json  # your own file, same format
    python manage.py seed_content --only-if-empty       # used on first start

File format: {"skills": [{"track","domain","name","slug","order","summary","lesson",
  "questions": [{"type","stem","choices","answer","difficulty","explanation","source"}]}]}
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from learn.models import Question, Skill

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "sample_questions.json"


def load_file(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    created_q = updated_q = 0
    with transaction.atomic():
        for entry in data["skills"]:
            skill, _ = Skill.objects.update_or_create(
                slug=entry["slug"],
                defaults={
                    "track": entry["track"],
                    "domain": entry["domain"],
                    "name": entry["name"],
                    "order": entry.get("order", 0),
                    "summary": entry.get("summary", ""),
                    "lesson": entry.get("lesson", ""),
                },
            )
            for item in entry.get("questions", []):
                answer_type = item.get("type", "choice")
                _, was_created = Question.objects.update_or_create(
                    skill=skill,
                    stem=item["stem"],
                    defaults={
                        "answer_type": answer_type,
                        "choices": item.get("choices", []) if answer_type == "choice" else [],
                        "correct_answer": str(item["answer"]),
                        "difficulty": item.get("difficulty", 2),
                        "explanation": item["explanation"],
                        "source_note": item.get("source", ""),
                    },
                )
                created_q += was_created
                updated_q += not was_created
    return created_q, updated_q


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_FILE))
        parser.add_argument("--only-if-empty", action="store_true")

    def handle(self, *args, **options):
        if options["only_if_empty"] and Skill.objects.exists():
            self.stdout.write("Skills already exist; not loading the sample questions.")
            return
        try:
            created, updated = load_file(options["file"])
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not load {options['file']}: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Questions added: {created}, updated: {updated}."))
