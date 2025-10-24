# Chatbot Design Training

A comprehensive Jekyll-based training website for information science graduate students learning chatbot design and implementation.

## Features

- **Navigation Bar**: Easy access to all training modules and chatbot program
- **Training Modules**: Four comprehensive modules covering:
  - Introduction to Chatbots
  - Conversation Design
  - User Experience Design
  - Implementation Strategies
- **Interactive Chatbot Demo**: Working chatbot with quick reply buttons and text input
- **Jekyll Theme**: Clean, professional appearance using the minima theme
- **Responsive Design**: Works on different screen sizes

## Getting Started

### Prerequisites

- Ruby 2.5.0 or higher
- Bundler gem

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/anjapope/chatbotdemo.git
   cd chatbotdemo
   ```

2. Install dependencies:
   ```bash
   bundle install
   ```

3. Build and serve the site locally:
   ```bash
   bundle exec jekyll serve
   ```

4. Open your browser and navigate to `http://localhost:4000`

## Deployment

### GitHub Pages

This site is ready to be deployed on GitHub Pages:

1. Go to your repository settings
2. Navigate to the "Pages" section
3. Select the branch you want to deploy (e.g., `main`)
4. Save the settings

GitHub Pages will automatically build and deploy your Jekyll site.

### Other Hosting Platforms

To deploy on other platforms:

1. Build the site:
   ```bash
   bundle exec jekyll build
   ```

2. The generated site will be in the `_site` directory
3. Upload the contents of `_site` to your hosting provider

## Project Structure

```
chatbotdemo/
├── _config.yml           # Jekyll configuration
├── index.md              # Homepage
├── chatbot.md            # Interactive chatbot demo
├── modules/              # Training modules
│   ├── introduction.md
│   ├── conversation-design.md
│   ├── user-experience.md
│   └── implementation.md
├── Gemfile               # Ruby dependencies
└── .gitignore            # Git ignore rules
```

## Customization

### Updating Content

- Edit markdown files in the root directory and `modules/` folder
- Modify `_config.yml` to change site title, description, and navigation

### Styling

The site uses the minima theme. To customize:

1. Create an `assets/main.scss` file
2. Add your custom CSS rules

### Chatbot Knowledge Base

Edit the `knowledgeBase` object in `chatbot.md` to add or modify chatbot responses.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

Built with Jekyll and the minima theme for educational purposes.