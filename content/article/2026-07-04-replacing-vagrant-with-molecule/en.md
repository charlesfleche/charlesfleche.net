---
title: Replacing Vagrant for Molecule
description: Making an Ansible safe development environment with molecule
og_image: molecule.png
tags: [linux, debian, ansible, molecule, vagrant, virtualbox]
---

![Molecule logo](molecule.png)


I recently rebuilt the local dev environment for a small Ansible project. Here's what I ended up with, and why.

# Why not Vagrant / VirtualBox

The old setup used Vagrant with the VirtualBox provider. That stopped being a good option on Debian: (trixie) [dropped VirtualBox from its repositories entirely](https://wiki.debian.org/VirtualBox) because of licensing issues with upstream. Getting VirtualBox running now means pulling packages from Oracle's own repository instead of the distro, which is extra friction for something that's supposed to be a quick `apt install`.

So I moved to [Molecule](https://ansible.readthedocs.io/projects/molecule/) with its [libvirt driver](https://github.com/ansible-community/molecule-libvirt), which talks to libvirt/QEMU directly, no Vagrant in the loop.

# Design goal: minimal duplication

My infrastructure is small, just a handful of machines, so I didn't want a heavyweight testing setup. The goal was to reuse as much of the production configuration as possible in dev, and keep the dev-only parts to a minimum.

# Inventory split

The [Ansible inventory](https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html#organizing-inventory-in-a-directory) lives in an `inventory/` folder, split into two files:

- `hosts.yml` defines each host's connection info (address, SSH user)
- `groups.yml` defines the groups and group membership

```yaml
# inventory/hosts.yml

all:
  hosts:
    vps2:
      ansible_host: vps-53fcb87d.vps.ovh.ca
      ansible_user: debian
```

```yaml
# inventory/groups.yml

servers:
  hosts:
    vps2:
```

`ansible.cfg` points at the whole folder by default, so production runs see both files:

```ini
# ansible.cfg

[defaults]

interpreter_python = /usr/bin/python3
inventory = inventory
vault_password_file=vault_password.sh
```

Molecule, on the other hand, is configured to only see `groups.yml`:

```yaml
# In molecule/default/molecule.yml

provisioner:
  name: ansible
  config_options:
    defaults:
      vault_password_file: "${MOLECULE_PROJECT_DIRECTORY}/vault_password.sh"
  inventory:
    links:
      hosts: "${MOLECULE_PROJECT_DIRECTORY}/inventory/groups.yml"
```

This one line does two things at once. First, the dev environment never sees production's connection info (addresses, SSH users) at all, so there's no risk of a test run accidentally touching a real host. Second, it avoids the usual clunky Molecule setup where you have to override every production host's connection details with fake VM ones. Molecule just generates its own host entries for the VMs it creates, and layers them under the same groups defined in `groups.yml`. Same group structure, no group logic duplicated between prod and dev.

# The scenario

Here's the full `molecule.yml`:

```yaml
# molecule/default/molecule.yml

---
dependency:
  name: galaxy
  options:
    requirements-file: requirements.yml

driver:
  name: libvirt

platforms:
  - name: vps2
    image_url: "https://saimei.ftp.acc.umu.se/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2"
    memory_size: 1 # GB
    vcpu: 1
    disk_size: "5G"
    qemu_user: "libvirt-qemu"

provisioner:
  name: ansible
  config_options:
    defaults:
      vault_password_file: "${MOLECULE_PROJECT_DIRECTORY}/vault_password.sh"
  inventory:
    links:
      hosts: "${MOLECULE_PROJECT_DIRECTORY}/inventory/groups.yml"
```

One platform, one Debian 13 cloud image, matching production closely enough to catch real issues.

# Adapting roles for dev with a fact

The other piece is `converge.yml`, the playbook Molecule runs against the VM:

```yaml
# molecule/default/converge.yml

---
- name: Setup dev environment
  hosts: all
  gather_facts: true
  tasks:
    - name: "Set deployment_is_dev to true"
      ansible.builtin.set_fact:
        deployment_is_dev: true

- name: Execute the root playbook
  ansible.builtin.import_playbook: "{{ lookup('env', 'MOLECULE_PROJECT_DIRECTORY') }}/playbook.yml"
```

It sets one fact, `deployment_is_dev`, then hands off to the real production playbook via [`ansible.builtin.import_playbook`](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/import_playbook_module.html). No dev-specific copy of the playbook to keep in sync. It's the exact same one used in production.

Roles can check `deployment_is_dev` and branch where needed. The main use case for me is SSL: in production, a role asks [Certbot](https://certbot.eff.org/) to issue a real certificate.During development, it just generates a self-signed one instead, so `molecule test` doesn't need internet access to an ACME server or a real domain name.

# Result

- Production and dev share the same groups, the same playbook, and the same roles.
- The only things that differ are the host connection details (which dev never even sees) and whatever a role explicitly branches on via `deployment_is_dev`.
- No Vagrant, no VirtualBox, no licensing headaches on Debian.

