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
gpg --import gpg/*<TAB>
gpg -d infinity.kdb.gpg > infinity.kdb
# Encrypt again:
gpg -e -o infinity.kdb.gpg -r gpg/* infinity.kdb
```


- Checkout this repository locally.
    - Work locally by simply `docker-compose up` ([convenience commandsb](https://gist.github.com/mindey/6b9f3c6eb5cac93b62d5abaa15a4d9ba))
    - Alternatively, without docker, [in plain pip and postgresql](https://gist.github.com/mindey/6aff869782800429a96500dba94db8b2).

- Deploy:
    - Via dockerhub: `docker pull inxyz/infinity-django`


