# ProjectRexa InkBloom

Welcome to ProjectRexa InkBloom, a versatile blog application built with Flask. This platform simplifies the process of creating, managing, and sharing your thoughts with the world.

## Screenshots

### Home Page

![Home Page](https://cdn.projectrexa.dedyn.io/projectrexa/blog/assets/2949a6852cb6a0cb8f70142beede2324)

### Blog Page View

![Blog Page View](https://cdn.projectrexa.dedyn.io/projectrexa/blog/assets/48fb095365c0219e3435f7da12ff3596)

## Getting Started

### Prerequisites

- Python (version 3.6 and above)
- Git
- MongoDB
- Redis

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/ProjectRexa/InkBloom.git
   ```

2. Navigate to the project directory:

   ```bash
   cd InkBloom
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root and set the following variables:

   ```env
   REDIS_URL=
   MONGODB_URL=
   MONGODB_DATABASE=
   ATHER_API_KEY=  # Custom private S3 upload API; modify the code to store files locally
   GITHUB_CLIENT_ID=
   GITHUB_CLIENT_SECRET=
   ```

5. Run the application:

   ```bash
   python app.py
   ```

The application will be accessible at `http://127.0.0.1:5000/` by default.

## Environment Variables

- `REDIS_URL`: URL for Redis, used for session management.
- `MONGODB_URL`: URL for MongoDB, the database used by the application.
- `MONGODB_DATABASE`: Name of the MongoDB database.
- `ATHER_API_KEY`: API key for Ather API, a custom private S3 upload API.
- `GITHUB_CLIENT_ID`: Client ID for GitHub OAuth.
- `GITHUB_CLIENT_SECRET`: Client Secret for GitHub OAuth.

Ensure these variables are properly configured in your `.env` file.

## Issues and Contributions

If you encounter any issues or have suggestions for improvement, please create an issue on GitHub. Contributions are welcome; feel free to fork the repository and submit a pull request.

## Contact

For any questions or feedback, contact the author:

- **Author**: Om Mishra
- **Email**: [contact@projectrexa.dedyn.io](mailto:contact@projectrexa.dedyn.io)

## Why ProjectRexa InkBloom?

- **Easy to Use**: ProjectRexa InkBloom is designed for simplicity and ease of use.
- **Flask Framework**: Built with Flask, a lightweight and easy-to-extend web framework for Python.

Feel free to reach out for any questions or feedback. Happy blogging with ProjectRexa InkBloom!
