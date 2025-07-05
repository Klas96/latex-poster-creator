# Poster API

A Flask-based API to generate posters from LaTeX templates.

## Features

- Composes posters from background, midground, and foreground LaTeX template layers.
- Allows dynamic population of `title` and `content` in the midground template via API parameters.
- Compiles the combined LaTeX source to PDF using `pdflatex`.
- Returns the generated PDF to the API user.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Ensure LaTeX is Installed:**
    A working LaTeX distribution with `pdflatex` accessible in your system's PATH is required for PDF generation. Common distributions include TeX Live (Linux, macOS, Windows), MiKTeX (Windows), and MacTeX (macOS).

## Running the Application

```bash
python app.py
```
The API will typically be available at `http://127.0.0.1:5001`.

## API Endpoint

### `/poster/compose`

-   **Method:** GET
-   **Description:** Composes a poster from specified templates, populates title and content, compiles to PDF, and returns the PDF.
-   **Query Parameters:**
    -   `background` (string, required): Name of the background template file (without `.tex` extension) from the `poster_templates/background/` directory.
    -   `midground` (string, required): Name of the midground template file (without `.tex` extension) from the `poster_templates/midground/` directory.
    -   `foreground` (string, required): Name of the foreground template file (without `.tex` extension) from the `poster_templates/foreground/` directory.
    -   `title` (string, optional): Title for the poster, inserted into the midground template.
    -   `content` (string, optional): Main content for the poster, inserted into the midground template.
-   **Success Response (200 OK):**
    -   `Content-Type: application/pdf`
    -   `Content-Disposition: attachment;filename=poster.pdf`
    -   Body: Raw PDF data.
-   **Error Responses:**
    -   `400 Bad Request` (JSON): If required template parameters are missing.
    -   `404 Not Found` (JSON): If specified template files are not found.
    -   `500 Internal Server Error` (JSON): If LaTeX compilation fails or other server-side errors occur. Includes a `compilation_log_preview` in case of compilation failure.

## Running Tests

The project uses Python's built-in `unittest` framework for testing.

1.  **Ensure all development dependencies are installed** (though for these tests, only Flask from `requirements.txt` is strictly needed besides Python itself).
2.  **Make sure `pdflatex` is installed and in your PATH**, as some tests rely on actual LaTeX compilation.
3.  **Navigate to the root directory of the project.**
4.  **Run the tests using the following command:**

    ```bash
    python -m unittest test_app.py
    ```
    Or, for more verbose output:
    ```bash
    python -m unittest -v test_app.py
    ```

This will discover and run all tests defined in `test_app.py`.
