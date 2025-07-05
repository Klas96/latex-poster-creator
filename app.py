from flask import Flask, request, jsonify
import os
from flask import Response # Added for custom content type

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
    raw_midground_content = ""
    final_foreground_content = "" # This will be processed or raw if title/content not provided

    # Read background template
    try:
        with open(bg_path, 'r', encoding='utf-8') as f:
            raw_background_content = f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to read background template: {background_template_name}.tex", "details": str(e)}), 500

    # Read midground template
    try:
        with open(mg_path, 'r', encoding='utf-8') as f:
            raw_midground_content = f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to read midground template: {midground_template_name}.tex", "details": str(e)}), 500

    # Process or read foreground template
    try:
        with open(fg_path, 'r', encoding='utf-8') as f:
            foreground_template_content = f.read()

        if title is not None and content is not None:
            # Substitute title and content if provided
            current_fg_content = foreground_template_content.replace('%%TITLE%%', title)
            final_foreground_content = current_fg_content.replace('%%CONTENT%%', content)
        else:
            # Use raw foreground content if title/content not provided
            final_foreground_content = foreground_template_content

    except Exception as e:
        return jsonify({"error": f"Failed to read or process foreground template: {foreground_template_name}.tex", "details": str(e)}), 500

    # Combine into master template
    try:
        combined_latex_doc = MASTER_LATEX_TEMPLATE.replace('%%BACKGROUND_CONTENT%%', raw_background_content)
        combined_latex_doc = combined_latex_doc.replace('%%MIDGROUND_CONTENT%%', raw_midground_content)
        combined_latex_doc = combined_latex_doc.replace('%%FOREGROUND_CONTENT%%', final_foreground_content)
    except Exception as e:
        # This would catch unexpected errors if content variables are not strings, etc.
        # Also good if MASTER_LATEX_TEMPLATE was somehow not loaded correctly (though it's a global constant here)
        return jsonify({"error": "Failed to combine LaTeX templates into master document.", "details": str(e)}), 500

    return Response(combined_latex_doc, mimetype='application/x-latex')

# --- Step 3: Remove or update the old /poster/{template_name} endpoint ---
# For now, let's remove the old endpoint as per the plan.
# If you want to keep it, for e.g. fetching a single template, we can adjust.

# @app.route('/poster/<template_name>')
# def get_poster_template(template_name):
#     return f"Placeholder for poster template: {template_name}"

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Changed port to avoid potential conflicts
