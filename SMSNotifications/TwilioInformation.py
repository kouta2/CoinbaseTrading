

class TwilioInformation:

    def __init__(self):
        with open('account_info.txt') as f:
            twilio_info = f.readlines()

        self.sid = (twilio_info[0].split(':'))[1].strip()
        self.token = (twilio_info[1].split(':'))[1].strip()
        self.twilio_phone = (twilio_info[2].split(':'))[1].strip()
        self.primary_phone = (twilio_info[3].split(':'))[1].strip()
        self.secondary_phone = (twilio_info[4].split(':'))[1].strip()

    def get_primary_phone(self):
        return self.primary_phone

    def get_secondary_phone(self):
        return self.secondary_phone