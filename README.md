# Infinity Project

[![Travis status](https://travis-ci.org/inxyz/infinity-django.svg?branch=base&style=flat)](https://travis-ci.org/inxyz/infinity-django)

Here will be documentation.

## Preprequisites.

```
+ Email Account
+ GitHub Account (github.com)
+ Dockerhub Account (docker.io)
+ Generate SSH keypair
+ Generate GPG keypair
+ Domain Name
+ Hosting Provider Account (ubuntu 16.04)
+ ReadTheDocs Account (readthedocs.io)
```

To use entire this repository with some different GitHub organization, DockerHub account, and Hosting Service, just look at the changes here, to see what [changes needs to be changed for CI](https://github.com/inxyz/infinity-django/compare/af7f280003a57b08e19cbba1dc2ffd75a89baf97...69c8d6728e6336e62fc16730f86c60c24ed953ee).

## Project devops:

All relevant information is available in `infinity.kdb.gpg`, which is a KeePassX file with same password as filename.

```
# decrypt:
gpg -d infinity.kdb.gpg > infinity.kdb

# encrypt:
1. import others' public keys
```
curl https://api.github.com/users/<GITHUB_USERNAME>/gpg_keys | jq -r ".[0].raw_key" | gpg --import -
```
2. check who is available
```
gpg --list-keys
```

2. encrypt to those people (currently: [mindey](https://api.github.com/users/mindey/gpg_keys))
gpg -e -o infinity.kdb.gpg -r <email> -r <email> infinity.kdb
```

- Checkout this repository locally.
    - Work locally by simply `docker-compose up` ([convenience commandsb](https://gist.github.com/mindey/6b9f3c6eb5cac93b62d5abaa15a4d9ba))
    - Alternatively, without docker, [in plain pip and postgresql](https://gist.github.com/mindey/6aff869782800429a96500dba94db8b2).

- Deploy:
    - Via dockerhub: `docker pull inxyz/infinity-django`

## Deploying a CI with A single node

- Create one Ubuntu 16.04 server.
- Map the DNS A records to the server domain (e.g., mydomain.com)
- Make sure you can ssh as root@mydomain.com

- Locally install ansible (at least ansible version 2.4.0.0)
- Install locally:
    - `ansible-galaxy install thefinn93.letsencrypt` (use at least ansible version 2.4.0.0)

- Replace "net.wfx.io" with mydomain.com in those files:
    - ./deploy/ansible/site.yml
    - ./deploy/ansible/inventories/staging/hosts
- Rename file:
    - ./deploy/ansible/inventories/staging/host_vars/test.wfx.io -> mydomain.com
- Review, change to your repo:
      ./deploy/ansible/roles/prepare/vars/main.yml

- Type, and wait for the server will be fully set up:
    - `ansible-playbook -v -i deploy/ansible/inventories/staging deploy/ansible/site.yml --extra-vars="scenario=init"`

- Run command to deploy:
    - `ANSIBLE_VAULT_PASSWORD_FILE=.vault_password.txt ansible-playbook -v -i deploy/ansible/inventories/staging deploy/ansible/site.yml`

- Finally, visit the:
    - https://mydomain.com


The service should be running (make sure to do Django migrations, create superuser, load database). [convenience commands](https://gist.github.com/mindey/34fb97b5082d551ccb3bf24602e243ff).
## Deployment from CI, Travis

- On Travis:
    - Set up DockerHub, and GitHub API key, and Ansible Vault keys:
    `https://travis-ci.org/<organization>/<project>/settings`

    - Go to GitHub Developer settings to generate the API key with all but delete rights:
    - `GITHUB_API_KEY`
    - Go to DockerHub and create a user.
    - `DOCKER_USERNAME`
    - `DOCKER_PASSWORD`

    - Use travis-cli (e.g., `sudo gem install travis --no-user-install`)
    - `VAULT_PASSWORD_KEY`

    - `travis login`
    - `travis encrypt VAULT_PASSWORD_KEY=<___> --add` to append a public key to .travis.yml (`secure` section), based on instructions here: [https://docs.travis-ci.com/user/encrypting-files/#Using-GPG](https://docs.travis-ci.com/user/encrypting-files/#Using-GPG)

    - Change the DockerHub variables according to your DockerHub account.:
        - `deploy/scripts/deploy.sh`
        - `docker-compose.yml`
        - `production.yml`

    - Create .vault_password.txt, and encrypt `.env` variables with Ansible Vault:
        `ANSIBLE_VAULT_PASSWORD_FILE=.vault_password.txt ansible-vault encrypt .env_production --output .env_production.vault`

    - Generate travis ssh key for deployment to server, and add `travis_rsa.pub` to `~/.ssh/authorized_keys` on server:
        `ssh-keygen -f travis_rsa -t rsa -b 2048 -C -N`
    
    - Encrypt the travis_rsa, with Ansible vault, like so:
        `ANSIBLE_VAULT_PASSWORD_FILE=.vault_password.txt ansible-vault encrypt travis_rsa --output travis_rsa.vault`

## Database download.

- Existing production servers:
    - test.wfx.io
    - test.wefindx.io
    - net.wfx.io
