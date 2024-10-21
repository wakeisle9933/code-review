# AI Code Review Project 🤖💻

Hello there! This project is an awesome system that automatically provides AI code reviews using GitHub Actions! 😎✨

## Key Features 🚀

- Automatic Pull Request reviews 👀
- Code change analysis 🔍
- Performance and optimization suggestions 💪
- Q&A with AI through comments 💬🧠
- Friendly and fun feedback 🎉

## Technologies Used 🛠️

- Python 🐍
- OpenAI API 🧠
- GitHub Actions ⚙️
- PyGithub library 🐙

## Getting Started 🏁

1. Clone this repository 💾
2. Check out the files in the `.github/workflows` folder 📂
3. Add your OpenAI API key to GitHub Secrets 🔑  
   3-1. Go to your GitHub Repository page and click on the "Settings" tab at the top ⚙️  
   3-2. In the left sidebar, expand "Secrets and variables" and select "Actions" 🔒  
   3-3. Click on the "New repository secret" button ➕  
   3-4. In the "Name" field, enter `OPENAI_API_KEY`, and in the "Secret" field, paste your OpenAI API key 🔑  
   3-5. Click the "Add secret" button to save it 💾  
   3-6. Follow the same steps to add `OPENAI_MODEL`! 🌟 You can choose any model name from this link (https://openai.com/api/pricing/)! If you don't set it, gpt-4o will be used as the default 🤖
4. Create a Pull Request targeting the master branch to receive awesome AI reviews! 🎭  
   4-1. If you want to apply AI reviews to other branches or multiple branches, modify the `branches` section in the `ai-code-review.yml` file like this:

   ```yaml
   on:
     pull_request:
       branches:
         - master
         - develop

   ```
   This will apply AI reviews to both master and develop branches! Feel free to add more branches as needed 😉👍

### Applying to Other Projects 🔄

Want to apply this cool AI review system to your own project? It's super easy! 👌

1. Copy the `.github/workflows` folder to your project 📋
2. Add your OpenAI API key to your GitHub Secrets (follow steps 3-1 to 3-5 above!) 🔐
3. If needed, modify the `branches` section in `ai-code-review.yml` to fit your project structure 🛠️
4. That's it! Now your Pull Requests will get awesome AI reviews too! 🎊

## Important Notes ⚠️

- Never make your API key public! Keep it secret, keep it safe 🤫
- The OPENAI_API_KEY has been removed from this shared repository to prevent excessive charges. As a result, AI Review won't work if you create a Pull Request in this repository. 🚫💸
- To use this AI Review system, you must register your own OPENAI_API_KEY in your individual repository. 🔐🔑
- Review content is for reference. The final decision is up to you! 💡