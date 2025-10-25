---
title: Static Files
description: Serving static files is a common requirement for web applications. Nexios provides a robust and flexible system for serving static assets like CSS, JavaScript, images, and other file types with security and performance in mind.
head:
  - - meta
    - property: og:title
      content: Static Files
  - - meta
    - property: og:description
      content: Serving static files is a common requirement for web applications. Nexios provides a robust and flexible system for serving static assets like CSS, JavaScript, images, and other file types with security and performance in mind.
---

# 📂 Static Files

Serving static files is a common requirement for web applications. Nexios provides a robust and flexible system for serving static assets like CSS, JavaScript, images, and other file types with security and performance in mind.

## 🚀 Basic Setup

To serve static files in Nexios, use the `StaticFiles` class:

```python
from nexios import NexiosApp
from nexios.static import StaticFiles

app = NexiosApp()

# Create a static files handler for a single directory
static_files = StaticFiles(directory="static")

# Register the static files handler with a prefix
app.register(static_files, prefix="/static")
```

With this setup, a file at `static/css/style.css` would be accessible at `/static/css/style.css`.

### Single Directory

The simplest configuration uses a single directory for all static files:

```python
static_files = StaticFiles(directory="static")
app.register(static_files, prefix="/static")
```

## 📁 Multiple Directories

For more complex setups, you can serve files from multiple directories:

```python
static_files = StaticFiles(directories=["static", "public/assets", "uploads"])
app.register(static_files, prefix="/static")
```

When serving from multiple directories, Nexios searches for files in the order the directories are specified.

## 🛣️ URL Prefixing

The `prefix` parameter defines the URL path under which static files are served:

```python
static_files = StaticFiles(directory="static")
app.register(static_files, prefix="/assets")  # Serve files at /assets/ instead of /static/
```


## 📚 Examples

### Complete Application Setup

```python
from nexios import NexiosApp
from nexios.static import StaticFiles

app = NexiosApp()

# Serve static files with optimizations
static_files = StaticFiles(
    directory="static",
    prefix="/static",
    cache_control="public, max-age=3600",
    gzip=True,
    allowed_extensions=["css", "js", "png", "jpg"]
)

app.register(static_files)

# Add middleware for logging
app.add_middleware(StaticFileLogger())
```

This setup provides a secure, performant, and flexible way to serve static files in your Nexios application.
