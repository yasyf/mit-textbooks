import paramiko, base64, os, re

def get_combo():
  pubkey = os.getenv('SSH_PUBKEY')
  paramiko_pubkey = paramiko.RSAKey(data=base64.b64decode(pubkey))
  client = paramiko.SSHClient()
  client.get_host_keys().add(os.getenv('SSH_HOST'), 'ssh-rsa', paramiko_pubkey)
  client.connect(os.getenv('SSH_HOST'), username=os.getenv('j_username'), password=os.getenv('j_password'))
  _, stdout, _ = client.exec_command('tellme combo')
  combo = re.search(r'\d{5}', stdout.read()).group(0)
  client.close()
  return combo
  