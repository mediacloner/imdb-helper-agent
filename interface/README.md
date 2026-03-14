# Phase 4: Output Delivery Interface

## Purpose
This directory contains the code for delivering guidance to the end-user via a conversational chat interface, built primarily using **React**.

## Mechanism
* **Chat Interface (React):** A responsive frontend application built in React where users interact with the system by asking questions.
* **Mixed Responses:** The React application handles and renders a combination of text explanations and visual guidance.
* **On-the-fly Video Generation:** The agent records a `.webm` or `.mp4` video of the process (via a backend Playwright script executing the retrieved pathway) and serves this video tutorial to the React frontend, which displays it alongside the text response in the chat interface.
