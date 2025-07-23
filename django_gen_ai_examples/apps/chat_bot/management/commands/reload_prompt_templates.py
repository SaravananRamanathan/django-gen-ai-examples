"""
Management command to truncate and reload PromptTemplate model from fixture.
"""

import json
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from chat_bot.models import PromptTemplate


class Command(BaseCommand):
    help = "truncate and reload PromptTemplate model."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            type=str,
            default="prompt_templates_fixture.json",
            help="Fixture filename to load from (default: prompt_templates_fixture.json)",
        )
        parser.add_argument(
            "--directory",
            type=str,
            default=None,
            help="fixture file location DIR (default: ./fixtures)",
        )
        parser.add_argument("--skip-confirmation", action="store_true", help="Skip confirmation prompts.")

    def handle(self, *args, **options):
        fixture_filename = options["fixture"]
        fixture_directory = options["directory"]
        skip_confirmation = options["skip_confirmation"]

        if fixture_directory:
            if not os.path.isabs(fixture_directory):
                fixture_directory = os.path.join(settings.BASE_DIR.parent, fixture_directory)
        else:
            # NOTE: Defaults to ./fixtures dir.
            fixture_directory = os.path.join(settings.BASE_DIR.parent, "fixtures")

        fixture_path = os.path.join(fixture_directory, fixture_filename)
        if not os.path.exists(fixture_path):
            self.stdout.write(self.style.ERROR(f"Fixture file not found: {fixture_path}"))
            return

        # Validate fixture:
        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                fixture_data = json.load(f)
            if not isinstance(fixture_data, list):
                self.stdout.write(self.style.ERROR("Fixture file is not valid: expected a list of objects."))
                return
            fixture_prompts_count = len(fixture_data)
            if fixture_prompts_count == 0:
                self.stdout.write(self.style.WARNING("No objects found in fixture file."))
                return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Invalid JSON in fixture file: {e}"))
            return
        except IOError as e:
            self.stdout.write(self.style.ERROR(f"Error reading fixture file: {e}"))
            return

        cur_prompts_count = PromptTemplate.objects.count()
        # Confirmation to Truncate and Reload PromptTemplate model:
        if not skip_confirmation:
            self.stdout.write(
                self.style.WARNING(
                    f"\nThis will:\n"
                    f"  - Delete all {cur_prompts_count} existing PromptTemplate objects\n"
                    f"  - Load {fixture_prompts_count} PromptTemplate objects from fixture\n"
                    f"  - Fixture file: {fixture_path}\n"
                )
            )

            confirm = input("Are you sure you want to proceed? [y/N]: ")
            if confirm.lower() not in ["y", "yes"]:
                self.stdout.write(self.style.ERROR("Prompt Reload Cancelled."))
                return

        with transaction.atomic():
            PromptTemplate.objects.all().delete()
            call_command("loaddata", fixture_path, verbosity=2)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully reloaded PromptTemplate model."
                f"\n  - Deleted: {cur_prompts_count} objects"
                f"\n  - Loaded: {PromptTemplate.objects.count()} objects"
            )
        )
