from flask import Flask, request, jsonify
import os
from flask import Response # Added for custom content type
import subprocess
import tempfile
import shutil # For robust directory removal, though tempfile.TemporaryDirectory handles it

app = Flask(__name__)

# Define the base directory for templates
TEMPLATE_BASE_DIR = "poster_templates"

MASTER_LATEX_TEMPLATE = r"""
\documentclass[landscape]{article} % Using landscape for a poster feel
\usepackage[utf8]{inputenc}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{tikz} % For potential advanced layering/graphics

% Poster dimensions (example: A0 size, common for posters)
% Adjust as needed, or make this configurable later
\geometry{paperwidth=118.9cm, paperheight=84.1cm, margin=2cm}

\pagestyle{empty} % No page numbers for a poster

\begin{document}

% --- Background Content ---
%%BACKGROUND_CONTENT%%

% --- Midground Content ---
%%MIDGROUND_CONTENT%%

% --- Foreground Content ---
%%FOREGROUND_CONTENT%%

\end{document}
"""

# Helper function for LaTeX compilation
def compile_latex_to_pdf(latex_source_string):
    """
    Compiles a given LaTeX source string to a PDF.
    Returns a tuple (pdf_content_bytes, error_log_string).
    If successful, pdf_content_bytes is the PDF data, error_log_string is None.
    If failed, pdf_content_bytes is None, error_log_string contains error info.
    """
    with tempfile.TemporaryDirectory() as temp_dir_name:
        tex_file_path = os.path.join(temp_dir_name, "poster.tex")
        pdf_file_path = os.path.join(temp_dir_name, "poster.pdf")
        log_file_path = os.path.join(temp_dir_name, "poster.log")

        try:
            with open(tex_file_path, 'w', encoding='utf-8') as f:
                f.write(latex_source_string)
        except Exception as e:
            return None, f"Error writing temporary .tex file: {str(e)}"

        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            f"-output-directory={temp_dir_name}",
            "-jobname=poster",
            tex_file_path
        ]

        compilation_log_details = ""
        compilation_success = False

        for i in range(2): # Run pdflatex twice
            try:
                process = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30) # Added timeout

                # Append stdout/stderr from pdflatex run
                if process.stdout:
                    compilation_log_details += f"\n--- Pass {i+1} STDOUT ---\n{process.stdout}"
                if process.stderr:
                    compilation_log_details += f"\n--- Pass {i+1} STDERR ---\n{process.stderr}"

                # Try to read the .log file for more detailed errors after each pass if process failed
                if process.returncode != 0:
                    if os.path.exists(log_file_path):
                        try:
                            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as log_f:
                                compilation_log_details += f"\n--- Pass {i+1} Full Log File (poster.log) ---\n" + log_f.read()
                        except Exception as log_e:
                            compilation_log_details += f"\n--- Error reading log file for pass {i+1}: {str(log_e)} ---"
                    else:
                        compilation_log_details += f"\n--- Pass {i+1} Log File (poster.log) not found. ---"
                    break # Stop if a pass fails

                if i == 1 and os.path.exists(pdf_file_path): # After second potentially successful pass
                    compilation_success = True

            except FileNotFoundError:
                return None, "pdflatex command not found. Ensure LaTeX is installed and in PATH."
            except subprocess.TimeoutExpired:
                return None, f"pdflatex command timed out after 30 seconds during pass {i+1}. LaTeX source might be too complex or stuck in a loop.\nLog so far:\n{compilation_log_details}"
            except Exception as e:
                return None, f"Error during pdflatex execution on pass {i+1}: {str(e)}\nLog so far:\n{compilation_log_details}"

        if compilation_success and os.path.exists(pdf_file_path):
            try:
                with open(pdf_file_path, 'rb') as f_pdf:
                    pdf_content = f_pdf.read()
                return pdf_content, None # pdf_content_bytes, no error_log_string
            except Exception as e:
                return None, f"Error reading generated PDF: {str(e)}"
        else:
            # Compilation failed or PDF not found after two passes
            final_error_message = "LaTeX compilation failed."
            if not os.path.exists(pdf_file_path):
                 final_error_message += " PDF file was not generated."

            # Ensure log_file_path content is captured if not already in compilation_log_details from a failed run
            if os.path.exists(log_file_path) and "Full Log File" not in compilation_log_details:
                try:
                    with open(log_file_path, 'r', encoding='utf-8', errors='replace') as log_f:
                        compilation_log_details += "\n--- Final Full Log File (poster.log) ---\n" + log_f.read()
                except Exception as log_e:
                    compilation_log_details += f"\n--- Error reading final log file: {str(log_e)} ---"

            if not compilation_log_details:
                compilation_log_details = "No detailed log was captured. Check pdflatex installation and .tex file syntax."

            return None, f"{final_error_message}\nDetails:\n{compilation_log_details}"

@app.route('/poster/compose', methods=['GET'])
def compose_poster():
    foreground_template_name = request.args.get('foreground')
    midground_template_name = request.args.get('midground')
    background_template_name = request.args.get('background')

    # --- Step 2: Basic error handling for missing parameters ---
    if not foreground_template_name:
        return jsonify({"error": "Missing 'foreground' template parameter"}), 400
    if not midground_template_name:
        return jsonify({"error": "Missing 'midground' template parameter"}), 400
    if not background_template_name:
        return jsonify({"error": "Missing 'background' template parameter"}), 400

    # Construct full paths
    # Assuming .tex extension for now. If other extensions are possible, this needs adjustment.
    fg_path = os.path.join(TEMPLATE_BASE_DIR, "foreground", f"{foreground_template_name}.tex")
    mg_path = os.path.join(TEMPLATE_BASE_DIR, "midground", f"{midground_template_name}.tex")
    bg_path = os.path.join(TEMPLATE_BASE_DIR, "background", f"{background_template_name}.tex")

    missing_files = []
    if not os.path.exists(fg_path):
        missing_files.append(f"Foreground template not found: {foreground_template_name}.tex")
    if not os.path.exists(mg_path):
        missing_files.append(f"Midground template not found: {midground_template_name}.tex")
    if not os.path.exists(bg_path):
        missing_files.append(f"Background template not found: {background_template_name}.tex")

    if missing_files:
        return jsonify({"error": "One or more template files not found", "details": missing_files}), 404

    # Get title and content parameters
    title = request.args.get('title')
    content = request.args.get('content')

    # Initialize content variables
    raw_background_content = ""
    processed_midground_content = "" # Renamed, as this will be processed
    raw_foreground_content = ""    # Renamed, as this is now always raw

    # Read background template
    try:
        with open(bg_path, 'r', encoding='utf-8') as f:
            raw_background_content = f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to read background template: {background_template_name}.tex", "details": str(e)}), 500

    # Read and process midground template
    try:
        with open(mg_path, 'r', encoding='utf-8') as f:
            midground_template_content = f.read()

        if title is not None and content is not None:
            # Substitute title and content into midground template if provided
            current_mg_content = midground_template_content.replace('%%TITLE%%', title)
            processed_midground_content = current_mg_content.replace('%%CONTENT%%', content)
        else:
            # Use raw midground content (with placeholders intact) if title/content not provided
            processed_midground_content = midground_template_content

    except Exception as e:
        return jsonify({"error": f"Failed to read or process midground template: {midground_template_name}.tex", "details": str(e)}), 500

    # Read foreground template (now always raw)
    try:
        with open(fg_path, 'r', encoding='utf-8') as f:
            raw_foreground_content = f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to read foreground template: {foreground_template_name}.tex", "details": str(e)}), 500

    # Combine into master template
    try:
        combined_latex_doc = MASTER_LATEX_TEMPLATE.replace('%%BACKGROUND_CONTENT%%', raw_background_content)
        combined_latex_doc = combined_latex_doc.replace('%%MIDGROUND_CONTENT%%', processed_midground_content) # Use processed midground
        combined_latex_doc = combined_latex_doc.replace('%%FOREGROUND_CONTENT%%', raw_foreground_content) # Use raw foreground
    except Exception as e:
        # This would catch unexpected errors if content variables are not strings, etc.
        # Also good if MASTER_LATEX_TEMPLATE was somehow not loaded correctly (though it's a global constant here)
        return jsonify({"error": "Failed to combine LaTeX templates into master document.", "details": str(e)}), 500

    # At this point, combined_latex_doc contains the full LaTeX source string.
    # Now, compile it to PDF.
    pdf_bytes, error_log = compile_latex_to_pdf(combined_latex_doc)

    if pdf_bytes:
        # Compilation successful, return the PDF
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': 'attachment;filename=poster.pdf'}
        )
    else:
        # Compilation failed, return an error message with the log
        # Be cautious about sending raw logs if they might contain sensitive info or be too large.
        # For now, we send a truncated log for easier debugging by the API user.
        max_log_length = 2000 # Truncate log to avoid overly large error responses
        truncated_log = error_log[:max_log_length] + ("..." if len(error_log) > max_log_length else "")

        error_response = {
            "error": "LaTeX compilation failed.",
            "details": "Could not generate PDF from the combined LaTeX source.",
            "compilation_log_preview": truncated_log
        }
        # It might be better to log the full error_log on the server for internal debugging.
        # print(f"LaTeX Compilation Failed. Full Log:\n{error_log}") # Server-side log
        return jsonify(error_response), 500 # Internal Server Error, as the compilation is a server-side process

# --- Step 3: Remove or update the old /poster/{template_name} endpoint ---
# For now, let's remove the old endpoint as per the plan.
# If you want to keep it, for e.g. fetching a single template, we can adjust.

# @app.route('/poster/<template_name>')
# def get_poster_template(template_name):
#     return f"Placeholder for poster template: {template_name}"

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Changed port to avoid potential conflicts
