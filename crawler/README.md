# Phase 1: Semantic Crawler

## Purpose
This directory contains the code for the Playwright semantic crawler. Its primary function is to explore the target website and extract its interactive capabilities without relying on standard text-scraping methods.

## Mechanism
A headless browser navigates the site. It parses the DOM for interactive elements (such as buttons, forms, links) and structural metadata (like ARIA roles) to understand the available actions on a page.

## Constraints
* **Human-like behavior:** The crawler must employ human-like behavior, including throttling speed, handling cookie banners appropriately, and using transparent User-Agents.
* **Avoid Detection:** These measures are crucial to avoid anti-bot detection mechanisms on target websites.
