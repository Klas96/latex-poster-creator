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


if __name__ == '__main__':
    unittest.main()
