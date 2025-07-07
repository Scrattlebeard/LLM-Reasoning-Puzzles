#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, and pipeline failures
IFS=$'\n\t'       # Stricter word splitting

# Recursive DNS resolution function
resolve_domain_recursively() {
    local domain="$1"
    local visited_domains="$2"
    local depth="$3"
    local max_depth=10
    local all_ips=()
    
    # Check depth limit
    if [ "$depth" -gt "$max_depth" ]; then
        echo "WARNING: Maximum DNS resolution depth ($max_depth) reached for $domain" >&2
        return 0
    fi
    
    # Check for loops
    if [[ " $visited_domains " =~ " $domain " ]]; then
        echo "WARNING: DNS resolution loop detected for $domain" >&2
        return 0
    fi
    
    # Add current domain to visited list
    local new_visited="$visited_domains $domain"
    
    echo "Resolving $domain (depth: $depth)..." >&2
    
    # First, check for CNAME records
    local cnames
    cnames=$(dig +short CNAME "$domain" 2>/dev/null || true)
    
    if [ -n "$cnames" ]; then
        echo "Found CNAME records for $domain:" >&2
        while read -r cname; do
            if [ -n "$cname" ]; then
                # Remove trailing dot if present
                cname=$(echo "$cname" | sed 's/\.$//')
                echo "  -> $cname" >&2
                
                # Recursively resolve CNAME target
                local cname_ips
                cname_ips=$(resolve_domain_recursively "$cname" "$new_visited" $((depth + 1)))
                if [ -n "$cname_ips" ]; then
                    while read -r ip; do
                        if [ -n "$ip" ]; then
                            all_ips+=("$ip")
                        fi
                    done < <(echo "$cname_ips")
                fi
            fi
        done < <(echo "$cnames")
    fi
    
    # Also check for direct A records
    local a_records
    a_records=$(dig +short A "$domain" 2>/dev/null || true)
    
    if [ -n "$a_records" ]; then
        echo "Found A records for $domain:" >&2
        while read -r ip; do
            if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
                echo "  -> $ip" >&2
                all_ips+=("$ip")
            fi
        done < <(echo "$a_records")
    fi
    
    # Return unique IPs
    if [ ${#all_ips[@]} -gt 0 ]; then
        printf '%s\n' "${all_ips[@]}" | sort -u
    fi
}

# Flush existing rules and delete existing ipsets
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
ipset destroy allowed-domains 2>/dev/null || true

# First allow DNS and localhost before any restrictions
# Allow outbound DNS
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
# Allow inbound DNS responses
iptables -A INPUT -p udp --sport 53 -j ACCEPT
# Allow outbound SSH
iptables -A OUTPUT -p tcp --dport 22 -j ACCEPT
# Allow inbound SSH responses
iptables -A INPUT -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT
# Allow localhost
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Create ipset with CIDR support
ipset create allowed-domains hash:net

# Fetch GitHub meta information and aggregate + add their IP ranges
echo "Fetching GitHub IP ranges..."
gh_ranges=$(curl -s https://api.github.com/meta)
if [ -z "$gh_ranges" ]; then
    echo "ERROR: Failed to fetch GitHub IP ranges"
    exit 1
fi

if ! echo "$gh_ranges" | jq -e '.web and .api and .git' >/dev/null; then
    echo "ERROR: GitHub API response missing required fields"
    exit 1
fi

echo "Processing GitHub IPs..."
while read -r cidr; do
    if [[ ! "$cidr" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        echo "ERROR: Invalid CIDR range from GitHub meta: $cidr"
        exit 1
    fi
    echo "Adding GitHub range $cidr"
    ipset add allowed-domains "$cidr"
done < <(echo "$gh_ranges" | jq -r '(.web + .api + .git)[]' | aggregate -q)

# Resolve and add other allowed domains with recursive resolution
for domain in \
    "registry.npmjs.org" \
    "api.anthropic.com" \
    "api2.cursor.sh" \
    "api3.cursor.sh" \
    "api4.cursor.sh" \
    "repo42.cursor.sh" \
    "marketplace.cursorapi.com" \
    "cursor-cdn.com" \
    "downloads.cursor.com" \
    "anysphere-binaries.s3.us-east-1.amazonaws.com" \
    "marketplace.visualstudio.com" \
    "download.visualstudio.microsoft.com" \
    "pypi.org" \
    "sentry.io" \
    "statsig.anthropic.com" \
    "statsig.com"; do
    
    echo "=== Resolving $domain recursively ==="
    ips=$(resolve_domain_recursively "$domain" "" 0)
    
    if [ -z "$ips" ]; then
        echo "ERROR: Failed to resolve any IPs for $domain"
        exit 1
    fi
    
    echo "Final IPs for $domain:"
    while read -r ip; do
        if [ -n "$ip" ]; then
            if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
                echo "ERROR: Invalid IP resolved for $domain: $ip"
                exit 1
            fi
            echo "Adding $ip for $domain"
            ipset add allowed-domains "$ip"
        fi
    done < <(echo "$ips")
    echo ""
done

# Get host IP from default route
HOST_IP=$(ip route | grep default | cut -d" " -f3)
if [ -z "$HOST_IP" ]; then
    echo "ERROR: Failed to detect host IP"
    exit 1
fi

HOST_NETWORK=$(echo "$HOST_IP" | sed "s/\.[0-9]*$/.0\/24/")
echo "Host network detected as: $HOST_NETWORK"

# Set up remaining iptables rules
iptables -A INPUT -s "$HOST_NETWORK" -j ACCEPT
iptables -A OUTPUT -d "$HOST_NETWORK" -j ACCEPT

# Set default policies to DROP first
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# First allow established connections for already approved traffic
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Then allow only specific outbound traffic to allowed domains
iptables -A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT

echo "Firewall configuration complete"
echo "Verifying firewall rules..."
if curl --connect-timeout 5 https://example.com >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - was able to reach https://example.com"
    exit 1
else
    echo "Firewall verification passed - unable to reach https://example.com as expected"
fi

# Verify GitHub API access
if ! curl --connect-timeout 5 https://api.github.com/zen >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - unable to reach https://api.github.com"
    exit 1
else
    echo "Firewall verification passed - able to reach https://api.github.com as expected"
fi