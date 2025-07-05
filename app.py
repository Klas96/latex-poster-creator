from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Define the base directory for templates
TEMPLATE_BASE_DIR = "poster_templates"

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

    processed_foreground_content = None
    # If title and content are provided, try to process the foreground template
    if title is not None and content is not None:
        try:
            with open(fg_path, 'r') as f:
                foreground_content = f.read()

            # Define placeholders and replace them
            # Using simple string replacement. For complex scenarios, a proper templating engine might be better.
            processed_foreground_content = foreground_content.replace('%%TITLE%%', title)
            processed_foreground_content = processed_foreground_content.replace('%%CONTENT%%', content)

            # For now, we'll include the processed content in the response.
            # Later, this would be part of the combined LaTeX document.

        except Exception as e:
            # Handle potential file read errors, though os.path.exists should have caught non-existence
            return jsonify({"error": "Failed to read or process foreground template", "details": str(e)}), 500

    response_data = {
        "message": "Templates selected. See processed_foreground_content if title/content provided.",
        "selected_templates": {
            "foreground": foreground_template_name,
            "midground": midground_template_name,
            "background": background_template_name
        },
        "custom_data_provided": {
            "title_provided": title is not None,
            "content_provided": content is not None
        },
        "expected_paths": {
            "foreground": fg_path,
            "midground": mg_path,
            "background": bg_path
        }
    }

    if processed_foreground_content is not None:
        response_data["processed_foreground_content_preview"] = processed_foreground_content[:500] + "..." # Preview
        # In a real scenario, you might return the full content, or use it to generate a PDF.

    return jsonify(response_data), 200

# --- Step 3: Remove or update the old /poster/{template_name} endpoint ---
# For now, let's remove the old endpoint as per the plan.
# If you want to keep it, for e.g. fetching a single template, we can adjust.

# @app.route('/poster/<template_name>')
# def get_poster_template(template_name):
#     return f"Placeholder for poster template: {template_name}"

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Changed port to avoid potential conflicts
