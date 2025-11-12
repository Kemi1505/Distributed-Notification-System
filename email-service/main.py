# email_service/main.py

import sys
import os
import pika
import json
import time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# --- Configuration ---
load_dotenv()
RABBITMQ_URL = os.getenv('RABBITMQ_URL') # e.g., 'amqp://guest:guest@localhost:5672/%2F'
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL')

# --- Idempotency Check (using a simple in-memory set for this example) ---
# In a real system, you would use Redis for this.
processed_request_ids = set()

# --- Email Sending Logic with Retries ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_email(to_email, subject, body):
    """Sends an email using SendGrid and includes retry logic."""
    print(f"Attempting to send email to {to_email}...")
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=body)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent successfully to {to_email}, status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}. Retrying...")
        raise  # Re-raise the exception to trigger tenacity's retry mechanism

# --- RabbitMQ Callback ---
def callback(ch, method, properties, body):
    """This function is called every time a message is received from the email.queue."""
    print("\n[+] Received a new message.")
    
    try:
        message_data = json.loads(body)
        request_id = message_data.get('request_id')

        # 1. Idempotency Check
        if request_id in processed_request_ids:
            print(f"Duplicate request detected: {request_id}. Ignoring.")
            ch.basic_ack(delivery_tag=method.delivery_tag) # Acknowledge to remove from queue
            return

        # --- Pretend to fetch user data and template ---
        # In a real system, you would make REST calls to the User and Template services here.
        user_email = message_data.get('user_data', {}).get('email', 'default@example.com')
        user_name = message_data.get('user_data', {}).get('name', 'User')
        template_body = f"<h1>Hello, {user_name}!</h1><p>This is your notification.</p>"
        # ------------------------------------------------

        # 2. Send the email with retry logic
        send_email(user_email, "Your Notification", template_body)

        processed_request_ids.add(request_id) # Mark as processed
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[✔] Successfully processed message {request_id}.")

    except Exception as e:
        print(f"[!] Failed to process message after all retries: {e}")
        # 3. Move to Dead-Letter Queue
        # We will configure this on the queue itself, so we just need to reject the message.
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        print(f"[-] Message moved to dead-letter queue.")

# --- Main Consumer Loop ---
def start_consumer():
    print("Starting email service consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    # Declare the queues
    channel.queue_declare(queue='email.queue', durable=True)
    # You would also declare the failed.queue and the exchange here in a real setup

    channel.basic_consume(queue='email.queue', on_message_callback=callback)

    print('[*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        start_consumer()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)