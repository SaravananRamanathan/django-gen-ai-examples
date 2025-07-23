"""
Management command to export all PromptTemplate data to a fixture file.
"""

import os

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand

from chat_bot.models import PromptTemplate


class Command(BaseCommand):
    help = "Export PromptTemplate model to a fixture file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="prompt_templates_fixture.json",
            help="Output filename for the fixture (default: 'prompt_templates_fixture.json')",
        )
        parser.add_argument(
            "--directory",
            type=str,
            default=None,
            help="Directory to save the fixture file (default: ./fixtures)",
        )

    def handle(self, *args, **options):
        output_filename = options["output"]
        output_directory = options["directory"]

        if output_directory:
            if not os.path.isabs(output_directory):
                output_directory = os.path.join(settings.BASE_DIR.parent, output_directory)
        else:
            # NOTE: Defaults to ./fixtures dir.
            output_directory = os.path.join(settings.BASE_DIR.parent, "fixtures")
        output_path = os.path.join(output_directory, output_filename)

        prompt_templates = PromptTemplate.objects.all()

        if not prompt_templates.exists():
            self.stdout.write(self.style.WARNING("No PromptTemplate objects found."))
            return

        # Serialize PromptTemplate objects:
        serialized_data = serializers.serialize(
            "json", prompt_templates, indent=2, use_natural_foreign_keys=True, use_natural_primary_keys=False
        )

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(serialized_data)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully exported {prompt_templates.count()} PromptTemplate objects to: {output_path}"
                )
            )
        except IOError as e:
            self.stdout.write(self.style.ERROR(f"Error writing to file {output_path}: {e}"))
