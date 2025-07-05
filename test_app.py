import unittest
import os
import tempfile
import shutil
from unittest.mock import patch

# Assuming your Flask app instance is named 'app' in 'app.py'
# If it's created via a function, e.g., create_app(), adjust accordingly.
from app import app # Import the Flask app instance

class TestApp(unittest.TestCase):

    def setUp(self):
        """Set up test environment before each test."""
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Create a temporary directory for test templates
        self.test_templates_root_dir = tempfile.mkdtemp() # This will be like 'poster_templates'

        # Create subdirectories for layers
        self.test_fg_dir = os.path.join(self.test_templates_root_dir, "foreground")
        self.test_mg_dir = os.path.join(self.test_templates_root_dir, "midground")
        self.test_bg_dir = os.path.join(self.test_templates_root_dir, "background")
        os.makedirs(self.test_fg_dir)
        os.makedirs(self.test_mg_dir)
        os.makedirs(self.test_bg_dir)

        # --- Create minimal valid template files for general use ---
        # Background template
        with open(os.path.join(self.test_bg_dir, "test_valid_bg.tex"), "w") as f:
            f.write("% Test Background Template\n\\newcommand{\\testBG}{BG_OK}")

        # Midground template (with placeholders)
        with open(os.path.join(self.test_mg_dir, "test_valid_mg.tex"), "w") as f:
            f.write("% Test Midground Template\n\\section*{%%TITLE%%}\n%%CONTENT%%\n\\newcommand{\\testMG}{MG_OK}")

        # Foreground template
        with open(os.path.join(self.test_fg_dir, "test_valid_fg.tex"), "w") as f:
            f.write("% Test Foreground Template\nThis is test foreground text.\n\\newcommand{\\testFG}{FG_OK}")

        # --- Create a midground template with a LaTeX error for specific tests ---
        with open(os.path.join(self.test_mg_dir, "test_error_mg.tex"), "w") as f:
            f.write("% Test Midground Template with Error\n\\section*{%%TITLE%%}\n%%CONTENT%%\n\\thisisalatexerror\n\\newcommand{\\testMGERR}{MG_ERR_OK}")

        # --- Create new specific templates for testing them ---
        # bg_gradient.tex (minimal version)
        with open(os.path.join(self.test_bg_dir, "test_bg_gradient.tex"), "w") as f:
            f.write("% Test Gradient BG\n\\begin{tikzpicture}[remember picture, overlay]\n\\shade[top color=yellow, bottom color=orange] (current page.south west) rectangle (current page.north east);\n\\end{tikzpicture}")

        # bg_image_placeholder.tex (minimal, needs a dummy image)
        # Create a dummy image file (e.g., a tiny PNG).
        # For simplicity in this text-based environment, I'll just create an empty file.
        # In a real scenario, this should be a valid tiny image.
        self.dummy_image_name = "dummy_image_for_test.png"
        with open(os.path.join(self.test_templates_root_dir, self.dummy_image_name), "wb") as f:
            # Smallest possible valid PNG (1x1 transparent pixel)
            f.write(bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000A49444154789C63000100000500010D0A2DB40000000049454E444145426082"))

        with open(os.path.join(self.test_bg_dir, "test_bg_image.tex"), "w") as f:
            f.write(f"% Test Image BG\n\\begin{{tikzpicture}}[remember picture, overlay]\n\\node at (current page.center) {{\\includegraphics[width=\\paperwidth, height=\\paperheight, keepaspectratio=false]{{{self.dummy_image_name}}}}};\n\\end{{tikzpicture}}")

        # mg_columns.tex (minimal)
        with open(os.path.join(self.test_mg_dir, "test_mg_columns.tex"), "w") as f:
            f.write("% Test Columns MG\n\\begin{center}\\Large %%TITLE%%\\end{center}\n\\begin{multicols}{2}\n%%CONTENT%%\n\\end{multicols}")

        # mg_boxed_content.tex (minimal)
        with open(os.path.join(self.test_mg_dir, "test_mg_boxed.tex"), "w") as f:
            f.write("% Test Boxed MG\n\\begin{center}\\begin{tikzpicture}\n\\node[draw=red, fill=red!10, inner sep=5pt] {{\\begin{minipage}{0.7\\textwidth}\\centering\\Large %%TITLE%%\\par\\small %%CONTENT%%\\end{minipage}}};\n\\end{tikzpicture}\\end{center}")


        # Patch the global TEMPLATE_BASE_DIR in app.py to use our temp directory
        # This requires that app.TEMPLATE_BASE_DIR is accessible and modifiable,
        # or that os.path.join is patched where TEMPLATE_BASE_DIR is used.
        # Let's try patching the global variable directly.
        self.patcher = patch('app.TEMPLATE_BASE_DIR', self.test_templates_root_dir)
        self.mock_template_base_dir = self.patcher.start()

    def tearDown(self):
        """Clean up test environment after each test."""
        # Stop the patcher
        self.patcher.stop()
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_templates_root_dir)

    # Test methods will be added here in subsequent steps

    def test_successful_pdf_generation(self):
        """Test successful PDF generation with valid inputs."""
        response = self.client.get('/poster/compose?'
                                   'foreground=test_valid_fg&'
                                   'midground=test_valid_mg&'
                                   'background=test_valid_bg&'
                                   'title=Test%20Title&'
                                   'content=Test%20Content%20for%20PDF')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertIn('attachment;filename=poster.pdf', response.headers['Content-Disposition'])

        # Check if the response data looks like a PDF
        self.assertTrue(response.data, "PDF response data is empty")
        # A simple check for PDF magic number. PDFs usually start with %PDF-
        self.assertTrue(response.data.startswith(b'%PDF-'), "Response data does not look like a PDF file.")

        # For more thorough testing, one might save response.data to a file
        # and try to open it with a PDF library or tool, but that's more involved.
        # E.g., temp_pdf_path = os.path.join(self.test_templates_root_dir, "test_output.pdf")
        # with open(temp_pdf_path, "wb") as f:
        #     f.write(response.data)
        # print(f"Test PDF saved to {temp_pdf_path}") # For manual inspection if needed

    def test_latex_syntax_error(self):
        """Test response when a LaTeX template has a syntax error."""
        response = self.client.get('/poster/compose?'
                                   'foreground=test_valid_fg&'
                                   'midground=test_error_mg&'  # Using the template with a LaTeX error
                                   'background=test_valid_bg&'
                                   'title=LaTeX%20Error%20Test&'
                                   'content=Content%20for%20error%20test')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.mimetype, 'application/json')

        json_response = response.get_json()
        self.assertIn('error', json_response)
        self.assertEqual(json_response['error'], 'LaTeX compilation failed.')
        self.assertIn('compilation_log_preview', json_response)

        # Check for an expected snippet from the LaTeX error log
        # The exact error message might vary slightly based on pdflatex version/OS,
        # but "Undefined control sequence" is common for \thisisalatexerror.
        self.assertIn('Undefined control sequence', json_response['compilation_log_preview'])
        self.assertIn('\\thisisalatexerror', json_response['compilation_log_preview'])

    def test_missing_template_file(self):
        """Test response when a specified template file is missing."""
        response = self.client.get('/poster/compose?'
                                   'foreground=non_existent_fg&'  # This template does not exist
                                   'midground=test_valid_mg&'
                                   'background=test_valid_bg&'
                                   'title=Missing%20File%20Test&'
                                   'content=Content')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.mimetype, 'application/json')

        json_response = response.get_json()
        self.assertIn('error', json_response)
        self.assertEqual(json_response['error'], 'One or more template files not found')
        self.assertIn('details', json_response)
        self.assertIsInstance(json_response['details'], list)
        self.assertIn('Foreground template not found: non_existent_fg.tex', json_response['details'])

    def test_missing_query_parameter(self):
        """Test response when a required query parameter is missing."""
        # Missing 'foreground' parameter
        response = self.client.get('/poster/compose?'
                                   # 'foreground=test_valid_fg&' # Omitted
                                   'midground=test_valid_mg&'
                                   'background=test_valid_bg&'
                                   'title=Missing%20Param%20Test&'
                                   'content=Content')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.mimetype, 'application/json')

        json_response = response.get_json()
        self.assertIn('error', json_response)
        self.assertEqual(json_response['error'], "Missing 'foreground' template parameter")

        # Test missing 'midground'
        response_mg = self.client.get('/poster/compose?'
                                      'foreground=test_valid_fg&'
                                      # 'midground=test_valid_mg&' # Omitted
                                      'background=test_valid_bg&'
                                      'title=Test&content=Test')
        self.assertEqual(response_mg.status_code, 400)
        json_response_mg = response_mg.get_json()
        self.assertEqual(json_response_mg['error'], "Missing 'midground' template parameter")

        # Test missing 'background'
        response_bg = self.client.get('/poster/compose?'
                                      'foreground=test_valid_fg&'
                                      'midground=test_valid_mg&'
                                      # 'background=test_valid_bg&' # Omitted
                                      'title=Test&content=Test')
        self.assertEqual(response_bg.status_code, 400)
        json_response_bg = response_bg.get_json()
        self.assertEqual(json_response_bg['error'], "Missing 'background' template parameter")

    @patch('app.subprocess.run') # Patch subprocess.run within the app module
    def test_pdflatex_not_found(self, mock_subprocess_run):
        """Test response when pdflatex command is not found."""
        # Configure the mock to raise FileNotFoundError when 'pdflatex' is the first arg
        def side_effect_for_pdflatex_cmd(*args, **kwargs):
            if args[0][0] == 'pdflatex': # Check if the command being run is pdflatex
                raise FileNotFoundError("Mock: pdflatex not found")
            # If it's some other command (not expected in this function, but good practice)
            # you could return a default mock or raise an error.
            # For this specific test, we only care about the pdflatex call.
            return unittest.mock.DEFAULT # Should not be reached in this test's context

        mock_subprocess_run.side_effect = side_effect_for_pdflatex_cmd

        response = self.client.get('/poster/compose?'
                                   'foreground=test_valid_fg&'
                                   'midground=test_valid_mg&'
                                   'background=test_valid_bg&'
                                   'title=PDFLatex%20Missing&'
                                   'content=Content')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.mimetype, 'application/json')

        json_response = response.get_json()
        self.assertIn('error', json_response)
        self.assertEqual(json_response['error'], 'LaTeX compilation failed.')
        self.assertIn('compilation_log_preview', json_response)
        self.assertIn('pdflatex command not found', json_response['compilation_log_preview'])

    def test_bg_gradient_template(self):
        """Test PDF generation with the gradient background template."""
        response = self.client.get('/poster/compose?'
                                   'foreground=test_valid_fg&'
                                   'midground=test_valid_mg&'
                                   'background=test_bg_gradient&' # New template
                                   'title=Gradient%20BG&'
                                   'content=Content%20with%20gradient')
        self.assertEqual(response.status_code, 200, f"Failed with gradient BG. Log: {response.data.decode('utf-8', errors='ignore') if response.status_code != 200 else ''}")
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF-'))

    def test_bg_image_template(self):
        """Test PDF generation with the image background template."""
        # Note: This test relies on the dummy_image_for_test.png created in setUp.
        # The actual image content isn't validated, just that pdflatex can find and include it without error.
        response = self.client.get('/poster/compose?'
                                   'foreground=test_valid_fg&'
                                   'midground=test_valid_mg&'
                                   'background=test_bg_image&' # New template
                                   'title=Image%20BG&'
                                   'content=Content%20with%20image%20bg')
        self.assertEqual(response.status_code, 200, f"Failed with image BG. Log: {response.data.decode('utf-8', errors='ignore') if response.status_code != 200 else ''}")
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF-'))

    def test_mg_columns_template(self):
        """Test PDF generation with the two-column midground template."""
        response = self.client.get('/poster/compose?'
                                   'foreground=test_valid_fg&'
                                   'midground=test_mg_columns&' # New template
                                   'background=test_valid_bg&'
                                   'title=Two%20Column%20Layout&'
                                   'content=This%20is%20the%20first%20column.%20\\newpage%20This%20is%20the%20second%20column.%20Lorem%20ipsum%20dolor%20sit%20amet.')
        self.assertEqual(response.status_code, 200, f"Failed with columns MG. Log: {response.data.decode('utf-8', errors='ignore') if response.status_code != 200 else ''}")
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF-'))

    def test_mg_boxed_template(self):
        """Test PDF generation with the boxed midground template."""
        response = self.client.get('/poster/compose?'
                                   'foreground=test_valid_fg&'
                                   'midground=test_mg_boxed&' # New template
                                   'background=test_valid_bg&'
                                   'title=Boxed%20Content&'
                                   'content=This%20content%20is%20inside%20a%20nice%20box.')
        self.assertEqual(response.status_code, 200, f"Failed with boxed MG. Log: {response.data.decode('utf-8', errors='ignore') if response.status_code != 200 else ''}")
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF-'))


if __name__ == '__main__':
    unittest.main()
