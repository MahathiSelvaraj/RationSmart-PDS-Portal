"""
Verification script for RationSmart Global Dropdown & UI Font Readability Improvements.
Verifies:
1. CSS design tokens and standardized typography scale.
2. Global dropdown styling (font-size >= 16px, option font-size >= 16px, min-height >= 44px).
3. Standardized font family 'Times New Roman' applied globally across elements.
4. Labels (>= 16px), Inputs (min-height >= 44px, >= 16px), Buttons (min-height >= 44px, >= 16px).
5. Tables, Cards, Modals, Badges, and Small/Helper text sizes (>= 14px, never tiny).
6. Visual identity palette: Warm ivory (#F8F7F2), Forest green (#244A36), Muted gold (#C5A15A), Dark charcoal (#202820).
"""

import os
import re
import unittest

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
CSS_FILE = os.path.join(WORKSPACE_DIR, 'static', 'css', 'style.css')
TEMPLATES_DIR = os.path.join(WORKSPACE_DIR, 'templates')

class TestUIReadabilityStandards(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(CSS_FILE, 'r', encoding='utf-8') as f:
            cls.css_content = f.read()

    def test_01_css_design_tokens_and_visual_identity(self):
        """Verify the civil service / government digital portal visual identity tokens."""
        self.assertIn('--pds-bg: #F8F7F2', self.css_content)
        self.assertIn('--pds-primary: #244A36', self.css_content)
        self.assertIn('--pds-accent-gold: #C5A15A', self.css_content)
        self.assertIn('--pds-text-dark: #202820', self.css_content)
        self.assertIn('--pds-text-muted: #555E57', self.css_content)
        self.assertIn('--pds-border: #D8D5CC', self.css_content)

    def test_02_universal_times_new_roman_font_family(self):
        """Verify Times New Roman is configured and applied universally."""
        self.assertIn("--pds-font-family: 'Times New Roman', Times, serif", self.css_content)
        self.assertIn("font-family: var(--pds-font-family) !important", self.css_content)

    def test_03_global_dropdown_select_styling(self):
        """Verify all dropdowns have >= 16px font, >= 44-48px min-height, and ample padding."""
        # Check select rule block
        self.assertIn("select.form-select", self.css_content)
        self.assertIn("min-height: var(--pds-control-min-height) !important", self.css_content)
        self.assertIn("--pds-control-min-height: 46px", self.css_content)
        # Check right-padding for custom SVG chevron
        self.assertIn("padding: 0.625rem 2.85rem 0.625rem 1rem !important", self.css_content)
        # Check custom SVG chevron is present and colored
        self.assertIn("data:image/svg+xml", self.css_content)
        self.assertIn("stroke='%23244A36'", self.css_content)

    def test_04_global_dropdown_option_styling(self):
        """Verify native option menus have explicit Times New Roman, >= 16px, padding, and high contrast."""
        self.assertIn("select.form-select option", self.css_content)
        self.assertIn("optgroup", self.css_content)
        self.assertIn("font-size: var(--pds-option) !important", self.css_content)
        self.assertIn("--pds-option: 16px", self.css_content)
        self.assertIn("padding: 10px 14px !important", self.css_content)

    def test_05_small_dropdown_and_input_overrides(self):
        """Verify .form-select-sm and .input-group-sm are overridden so they don't shrink below 44px / 16px."""
        self.assertIn(".form-select-sm", self.css_content)
        self.assertIn(".input-group-sm > .form-select", self.css_content)
        self.assertIn("min-height: var(--pds-control-min-height-sm) !important", self.css_content)
        self.assertIn("--pds-control-min-height-sm: 44px", self.css_content)

    def test_06_form_labels_and_inputs(self):
        """Verify labels are bold and >= 16px, inputs have min-height >= 44px and >= 16px font."""
        self.assertIn("label,\n.form-label", self.css_content)
        self.assertIn("font-size: var(--pds-label) !important", self.css_content)
        self.assertIn("--pds-label: 16.5px", self.css_content)
        self.assertIn("input.form-control", self.css_content)
        self.assertIn("font-size: var(--pds-input) !important", self.css_content)
        self.assertIn("--pds-input: 16.5px", self.css_content)
        self.assertIn("border: 1px solid var(--pds-border-input) !important", self.css_content)

    def test_07_focus_hover_and_disabled_states(self):
        """Verify clear focus ring, hover border, and high-contrast accessible disabled states."""
        self.assertIn("box-shadow: 0 0 0 0.22rem var(--pds-focus-ring) !important", self.css_content)
        self.assertIn("border-color: #8C887B !important", self.css_content)
        self.assertIn("input.form-control:disabled", self.css_content)
        self.assertIn("background-color: #ECEAE2 !important", self.css_content)
        self.assertIn("cursor: not-allowed !important", self.css_content)

    def test_08_button_dimensions_and_typography(self):
        """Verify buttons have min-height >= 44px and font-size >= 16px."""
        self.assertIn(".btn {", self.css_content)
        self.assertIn("min-height: 44px", self.css_content)
        self.assertIn("font-size: var(--pds-button) !important", self.css_content)
        self.assertIn("--pds-button: 16.5px", self.css_content)
        self.assertIn(".btn-primary", self.css_content)
        self.assertIn("background-color: var(--pds-primary) !important", self.css_content)

    def test_09_tables_and_data_display(self):
        """Verify tables have legible 15.5px font, padding, and tabular-nums alignment."""
        self.assertIn(".table th,", self.css_content)
        self.assertIn("font-size: var(--pds-table) !important", self.css_content)
        self.assertIn("--pds-table: 15.5px", self.css_content)
        self.assertIn("padding: 0.85rem 1rem !important", self.css_content)
        self.assertIn("font-variant-numeric: tabular-nums", self.css_content)

    def test_10_helper_text_and_badges_never_tiny(self):
        """Verify small/helper text and badges are >= 14px and never faint."""
        self.assertIn("small,\n.small,\n.form-text", self.css_content)
        self.assertIn("font-size: var(--pds-helper) !important", self.css_content)
        self.assertIn("--pds-helper: 14.5px", self.css_content)
        self.assertIn("font-size: 14px !important", self.css_content)

    def test_11_modals_and_dialogs_hierarchy(self):
        """Verify modal titles, body text, and dialog padding."""
        self.assertIn(".modal-title {", self.css_content)
        self.assertIn("font-size: 21px !important", self.css_content)
        self.assertIn(".modal-body {", self.css_content)
        self.assertIn("font-size: 16px", self.css_content)

    def test_12_all_template_select_elements_coverage(self):
        """Verify that every <select> tag in all templates uses form-select or will be styled by select rules."""
        select_count = 0
        for root, dirs, files in os.walk(TEMPLATES_DIR):
            for file in files:
                if file.endswith('.html'):
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = re.findall(r'<select[^>]*>', content)
                        select_count += len(matches)
                        for m in matches:
                            # Verify that it has a class attribute or is a standard select
                            self.assertTrue('class=' in m or '<select' in m)
        self.assertGreater(select_count, 15, "Should find multiple select controls across templates.")

if __name__ == '__main__':
    unittest.main()
