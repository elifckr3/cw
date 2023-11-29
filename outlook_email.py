import smtplib
from email.message import EmailMessage


def send_outlook_email(to_email, subject, email_body):

    try:
        # Create the email message
        email = EmailMessage()
        email['From'] = 'elifcakir.ccw@outlook.com'
        email['To'] = to_email
        email['Subject'] = subject
        email.set_content(email_body)

        # Set up the SMTP server
        server = smtplib.SMTP(host='smtp.office365.com', port=587)
        server.starttls()  # Start TLS encryption

        # Log in to your email account
        server.login('elifcakir.ccw@outlook.com', 'Workaccount123!!ccw')

        # Send the email
        server.send_message(email)

        # Confirmation message
        print("Email sent!")
        return "Email sent successfully!"

    except Exception as e:
        print(f"An error occurred: {e}")
        return "Failed to send email."

    # Close the connection to the SMTP server
    server.quit()


if __name__ == "__main__":
    send_outlook_email()