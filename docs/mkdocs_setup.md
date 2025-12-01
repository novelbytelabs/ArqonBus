# MkDocs Setup Guide

## Installation Requirements

To use the updated mkdocs configuration with Material theme and enhanced features, install the following packages:

### Required Packages

```bash
# Core mkdocs
pip install mkdocs

# Material theme for MkDocs
pip install mkdocs-material

# Optional but recommended for enhanced features
pip install mkdocs-macros-plugin
pip install pymdown-extensions
```

### Using Conda Environment (Recommended)

If you're using the helios-gpu-118 conda environment as specified in the project:

```bash
# Activate the conda environment
conda activate helios-gpu-118

# Install mkdocs and material theme
pip install mkdocs mkdocs-material

# Optional: Install additional extensions
pip install pymdown-extensions mkdocs-macros-plugin
```

### Verify Installation

```bash
# Check if mkdocs is installed and working
mkdocs --version

# Should show something like:
# mkdocs, version 1.5.3 from /path/to/site-packages/mkdocs (Python 3.10)
```

## Using MkDocs

### Build Documentation

```bash
# Build the documentation site
mkdocs build

# Serve locally for development
mkdocs serve
```

### Expected Output Structure

After building, the documentation will be available in the `site/` directory:

```
site/
├── index.html
├── getting-started/
│   ├── quickstart/
│   └── tutorial/
├── operations/
│   └── runbook/
├── developer-guide/
│   ├── developers-guide/
│   └── api/
├── architecture/
│   ├── architecture/
│   └── project-scope/
└── project-info/
    ├── ecosystem/
    └── completion-report/
```

## Features Included

### Material Theme Features
- ✅ Navigation sections and expandable menus
- ✅ Search with suggestions and highlighting
- ✅ Code annotation and copy functionality
- ✅ Content tabs and collapsible sections
- ✅ Responsive design and mobile support

### Markdown Extensions
- ✅ Syntax highlighting for code blocks
- ✅ Task lists with custom checkboxes
- ✅ Tables and admonitions
- ✅ Tabbed content
- ✅ Collapsible details
- ✅ Progress bars
- ✅ Magic links (automatic URL linking)

### Development Features
- ✅ Live preview server (`mkdocs serve`)
- ✅ GitHub-style edit links
- ✅ SEO optimization
- ✅ Social media integration
- ✅ Analytics support (Google Analytics)

## Troubleshooting

### Common Issues

#### 1. Module Not Found Error
```bash
# If you get "module not found" errors
pip install --upgrade mkdocs mkdocs-material
```

#### 2. Theme Not Loading
```bash
# Ensure the theme is properly installed
pip list | grep mkdocs
# Should show mkdocs and mkdocs-material
```

#### 3. Extensions Not Working
```bash
# Install Pymdown extensions for advanced features
pip install pymdown-extensions
```

### Alternative Installation (System-wide)

If conda environment approach doesn't work:

```bash
# Install globally (requires sudo on some systems)
pip3 install mkdocs mkdocs-material

# Or use virtual environment
python3 -m venv mkdocs-env
source mkdocs-env/bin/activate  # Linux/Mac
# mkdocs-env\Scripts\activate  # Windows
pip install mkdocs mkdocs-material
```

## Quick Start Commands

```bash
# 1. Install requirements (choose one method above)
pip install mkdocs mkdocs-material

# 2. Navigate to project directory
cd /path/to/arqonbus

# 3. Start development server
mkdocs serve

# 4. Open browser to http://localhost:8000
# 5. For production build:
mkdocs build

# 6. Deploy the site/ directory to your web server
```

## File Structure

The mkdocs.yml expects this file structure:

```
.
├── mkdocs.yml          # MkDocs configuration
├── docs/               # Documentation source files
│   ├── index.md
│   ├── quickstart.md
│   ├── tutorial.md
│   ├── runbook.md
│   ├── developers_guide.md
│   ├── api.md
│   ├── architecture.md
│   ├── arqonbus_v1_scope.md
│   ├── arqon_ecosystem.md
│   └── completion_report.md
└── stylesheets/
    └── extra.css       # Custom styles
```

## Additional Notes

- All the markdown files listed in the navigation are already created
- The configuration includes all 10 documentation files we've created
- The site is optimized for search and user feedback
- Material theme provides excellent mobile responsiveness
- Built-in GitHub integration for collaboration