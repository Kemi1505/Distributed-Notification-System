# Email Service - Distributed Notification System

This directory contains the source code for the **Email Service**, a specialized microservice that is a core component of the HNG Stage 4 Distributed Notification System.

## 1. Overview

The Email Service is a background worker, not a traditional web server. Its sole responsibility is to consume email notification tasks from a message queue, process them, and send emails via a third-party API.

This asynchronous, consumer-based architecture makes the overall notification system highly scalable and resilient. Even if the Email Service is temporarily offline or overwhelmed, notification requests will safely queue up in RabbitMQ and be processed once the service is available, ensuring no data is lost.

### Key Responsibilities:
-   **Consume Messages:** Listens exclusively to the `email.queue` on the shared RabbitMQ server.
-   **Send Emails:** Uses the Twilio SendGrid API to handle email delivery. It does not handle raw SMTP.
-   **Handle Failures:** Implements a robust retry mechanism with exponential backoff for transient failures (e.g., temporary network issues with the SendGrid API).
-   **Dead-Lettering:** After a configurable number of retries (currently 3), permanently failed messages are rejected and routed to a `failed.queue` (Dead-Letter Queue) for manual inspection.
-   **Idempotency:** Checks a unique `request_id` for each message to prevent processing the same notification multiple times in case of duplicate messages.
-   **Integration:** (Future work) Designed to communicate with the User Service and Template Service via REST APIs to fetch user details and email templates.

## 2. Technology Stack

-   **Language:** Python
-   **Message Broker:** RabbitMQ (via the `pika` library)
-   **Email Delivery:** Twilio SendGrid (via the `sendgrid` library)
-   **Retry Mechanism:** `tenacity`
-   **Environment Management:** `python-dotenv`

## 3. Local Setup and Installation

Follow these steps precisely to get the Email Service running on your local machine for development and testing.

### Prerequisites

-   Python 3.11+
-   Git

### Step-by-Step Guide

1.  **Clone the Repository:**
    If you haven't already, clone the main project repository.
    ```bash
    git clone https://github.com/Kemi1505/Distributed-Notification-System.git
    ```

2.  **Navigate to the Service Directory:**
    All subsequent commands must be run from within this specific service's folder.
    ```bash
    cd Distributed-Notification-System/email-service
    ```

3.  **Create and Activate a Virtual Environment:**
    This isolates the project's dependencies from your system's global Python installation.
    ```bash
    # Create the virtual environment folder named 'venv'
    python -m venv venv

    # Activate the environment (for Windows)
    .\venv\Scripts\activate
    ```
    Your terminal prompt should now be prefixed with `(venv)`.

4.  **Install Dependencies:**
    This command reads the `requirements.txt` file and installs all the necessary Python libraries into your virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

## 4. Environment Configuration (Critical Step)

This service relies on secret keys and external service URLs. These are managed in a `.env` file, which is **intentionally excluded from GitHub** for security.

1.  **Create the `.env` File:**
    In the root of the `email-service` directory, create a new file named exactly `.env`.

2.  **Add the Required Variables:**
    Copy the template below and paste it into your new `.env` file.

    ```env
    # --- Environment Variables for Email Service ---

    # 1. RabbitMQ Connection URL
    # Get this from your shared CloudAMQP instance dashboard.
    RABBITMQ_URL=amqp://user:password@hostname.rmq.cloudamqp.com/vhost

    # 2. SendGrid API Key
    # Create this in your SendGrid account under Settings > API Keys.
    SENDGRID_API_KEY=SG.your_very_long_and_secret_api_key_here

    # 3. Verified Sender Email
    # This must be an email address you have verified as a "Single Sender" in your SendGrid account.
    FROM_EMAIL=your-verified-email@example.com
    ```

3.  **How to Get the Values:**
    -   **`RABBITMQ_URL`**: This is the shared connection string for our team's RabbitMQ server. This should be provided by the team member who set up the CloudAMQP instance.
    -   **`SENDGRID_API_KEY`**: Log in to your [SendGrid](https://sendgrid.com/) account. Navigate to **Settings > API Keys** and create a new key with "Full Access". **Copy the key immediately**, as it will only be shown once.
    -   **`FROM_EMAIL`**: In SendGrid, navigate to **Settings > Sender Authentication** and complete the "Single Sender Verification" process for the email address you want to send from. Use that exact, verified email address here.

## 5. Running the Service

Once your dependencies are installed and your `.env` file is configured, you can start the service.

```bash
python main.py
```

If the setup is correct, the script will connect to RabbitMQ and begin listening. You will see the following output, and the program will continue to run:
```
Starting email service consumer...
[*] Waiting for messages. To exit press CTRL+C
```
The service is now active and ready to process jobs from the `email.queue`.

## 6. Message Contract

To trigger this service, another service (primarily the API Gateway) must publish a message to the RabbitMQ exchange, routed to the `email.queue`. The message payload **must** be a JSON string with the following structure:

```json
{
  "request_id": "a-unique-uuid-for-this-request",
  "user_data": {
    "email": "recipient@example.com",
    "name": "Recipient Name"
  }
}
```
-   **`request_id`**: A unique identifier (e.g., a UUID) for the notification request. This is used by the Email Service to prevent processing the same job twice (idempotency).
-   **`user_data`**: An object containing the necessary information to personalize and send the email. *Note: In the final architecture, this object might just contain a `user_id`, and the Email Service will be responsible for fetching the full user details from the User Service.*