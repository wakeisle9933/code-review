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
- OpenAI/OpenRouter API 🧠
- GitHub Actions ⚙️
- PyGithub library 🐙

## Getting Started 🏁

1. Clone this repository 💾
2. Check out the files in the `.github/workflows` folder 📂
3. Set up GitHub Secrets and Variables 🔑

   ### Setting Up Variables ⚙️
   3-1. Go to your GitHub Repository page and click on the "Settings" tab at the top ⚙️  
   3-2. In the left sidebar, expand "Secrets and variables" and select "Actions" 🔒  
   3-3. Select the "Variables" tab and click on "New repository variable" ➕  
   3-4. Set up the following variables:
   - `AI_PROVIDER`: Choose either 'openai' or 'openrouter' 🤖
   - `OPENAI_MODEL`: (Optional) Set OpenAI model name (defaults to gpt-4o if not set) 🌟
   - `OPENROUTER_MODEL_ID`: (Optional) Set OpenRouter model ID (defaults to anthropic/claude-3.5-sonnet if not set) 🎯

   ### Setting Up Secrets 🔐
   3-5. Select the "Secrets" tab and click on "New repository secret" ➕  
   3-6. Add the required secret based on your AI_PROVIDER:
   - For OpenAI: Add `OPENAI_API_KEY` 🔑
   - For OpenRouter: Add `OPENROUTER_API_KEY` 🗝️

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
2. Set up GitHub Secrets and Variables (follow step 3 above!) 🔐
3. If needed, modify the `branches` section in `ai-code-review.yml` to fit your project structure 🛠️
4. That's it! Now your Pull Requests will get awesome AI reviews too! 🎊

## Important Notes ⚠️

- Never make your API key public! Keep it secret, keep it safe 🤫
- The API keys have been removed from this shared repository to prevent excessive charges. As a result, AI Review won't work if you create a Pull Request in this repository 🚫💸
- To use this AI Review system, you must register your own API keys in your individual repository 🔐🔑
- Review content is for reference. The final decision is up to you! 💡
