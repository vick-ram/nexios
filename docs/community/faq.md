---
title: Frequently Asked Questions
icon: faq
description: >
    Frequently Asked Questions
head:
  - - meta
    - property: og:title
      content: Frequently Asked Questions
    - property: og:description
      content: Frequently Asked Questions
---
## Open Source & Community

### Is Nexios really free and open source?
Yes! Nexios is 100% open source and released under the MIT License. This means:
- You can use it for any purpose, including commercial projects
- You can modify and distribute the code
- No licensing fees or restrictions
- Full access to the source code on GitHub

### What is the nexios-contrib package?
The nexios-contrib package is a community-driven collection of extensions and middleware for Nexios. It includes:
- Middleware for common web development needs (ETag, URL normalization, security)
- Integrations with popular services and tools
- Community-contributed packages that extend Nexios functionality
- All packages are independently versioned and can be installed separately

### How can I contribute to Nexios?
There are many ways to contribute:
- **Code contributions**: Submit bug fixes, features, or improvements to the core framework
- **Community packages**: Create middleware or extensions for nexios-contrib
- **Documentation**: Help improve our docs, tutorials, and examples
- **Community support**: Answer questions and help other developers
- **Testing**: Report bugs and test new features

### Can I create commercial products with Nexios?
Absolutely! The MIT License allows you to use Nexios in commercial products without any restrictions. Many companies use Nexios to build their APIs and web services.

## Framework Design

### Why isn't Nexios built on Starlette?
Nexios was designed from the ground up to provide a more opinionated and streamlined experience compared to Starlette. While Starlette is a great ASGI framework, Nexios makes different architectural choices to optimize for:
- Performance through Rust-based core components
- Simpler, more intuitive API design
- Tighter integration with modern Python features
- Built-in best practices for web development

### Why does Nexios use Uvicorn?
Nexios uses Uvicorn as its default ASGI server because:
- It's one of the fastest ASGI servers available
- Built-in support for HTTP/2 and WebSockets
- Excellent performance with async/await Python code
- Active maintenance and wide adoption in the Python community
- Seamless integration with ASGI applications

## Deployment

### How to use Gunicorn with Nexios?
To deploy Nexios with Gunicorn, follow these steps:

1. Install Gunicorn and Uvicorn workers:
   ```bash
   pip install gunicorn uvicorn[standard]
   ```

2. Create a `wsgi.py` file:
   ```python
   from your_app import app

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run("wsgi:app", host="0.0.0.0", port=8000, reload=True)
   ```

3. Run with Gunicorn:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker wsgi:app
   ```

   - `-w`: Number of worker processes
   - `-k`: Worker class (Uvicorn worker)

