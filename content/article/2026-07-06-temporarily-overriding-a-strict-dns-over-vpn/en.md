Title: Temporarily overriding a strict DNS over VPN
Description: Corporation says no to VPN connection over Mullvad
Tags:# Temporarily overriding systemd-resolved DNS when Mullvad is too strict

My default setup locks DNS resolution to my [Mullvad](https://mullvad.net) VPN connection only. Mullvad is also my default route for all internet traffic. A firewall rule adds another security layer, blocking anything not routed through the VPN: all outbound traffic goes through the VPN.

This works great until I need to connect to my corporate VPN, which explicitly disallow connecting over Mullvad.

## Before: DNS locked to Mullvad

```bash
resolvectl status
```

```
# ...

Link 2 (eno1)
    Current Scopes: LLMNR/IPv4 LLMNR/IPv6
     Default Route: no

Link 4 (wg-mullvad-ca)
    Current Scopes: DNS
Current DNS Server: 100.64.0.7
       DNS Servers: 100.64.0.7
        DNS Domain: ~.
     Default Route: yes

# ...
```

`eno1` has no DNS scope and no default route; `wg-mullvad-ca` holds both, plus a `~.` routing domain, which makes it the catch-all resolver for everything.

## Resetting the global DNS

After dropping the firewall and the Mullvad connecting, a global DNS needs to be set to allow resolving on `eno1`.

```bash
sudo resolvectl dns eno1 9.9.9.9
sudo resolvectl default-route eno1 yes
```

## After: eno1 takes over

```
Link 2 (eno1)
    Current Scopes: DNS LLMNR/IPv4 LLMNR/IPv6
Current DNS Server: 9.9.9.9
       DNS Servers: 9.9.9.9
     Default Route: yes

Link 4 (wg-mullvad-ca)
    Current Scopes: none
Current DNS Server: 100.64.0.7
       DNS Servers: 100.64.0.7
        DNS Domain: ~.
     Default Route: yes
```

Note both links now claim `Default Route: yes`. It's not a big deal to here: `wg-mullvad-ca` is not active connection anymore, so nothing will be routed to it anyway.

## Verifying resolution actually moved

```bash
resolvectl query example.com
```

Output includes the answering link and server:

```
example.com: 2606:4700:10::6814:179a           -- link: eno1
             2606:4700:10::ac42:93f3           -- link: eno1
             172.66.147.243                    -- link: eno1
             104.20.23.154                     -- link: eno1

-- Information acquired via protocol DNS in 1.4ms.
-- Data is authenticated: no; Data was acquired via local or encrypted transport: no
-- Data from: cache
```

To confirm it's not the Mullvad tunnel silently still handling it, force each path explicitly and compare:

```bash
resolvectl query --interface=eno1 example.com
```
```
example.com: 2606:4700:10::6814:179a           -- link: eno1
             2606:4700:10::ac42:93f3           -- link: eno1
             172.66.147.243                    -- link: eno1
             104.20.23.154                     -- link: eno1

-- Information acquired via protocol DNS in 14.9ms.
-- Data is authenticated: no; Data was acquired via local or encrypted transport: no
-- Data from: cache network
```
```bash
resolvectl query --interface=wg-mullvad-ca example.com
```
```
example.com: resolve call failed: No appropriate name servers or networks for name found
```

