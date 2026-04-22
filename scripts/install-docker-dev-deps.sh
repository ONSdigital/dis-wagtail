apt --quiet --yes update
apt --quiet --yes install \
    git \
    gnupg \
    less \
    openssh-client \
    sudo
# Download and import the Nodesource GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
# Create NodeSource repository
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
# Update lists again and install Node.js
apt --quiet --yes update
apt --quiet --yes install nodejs
# Tidy up
apt --quiet --yes autoremove
rm -rf /var/lib/apt/lists/*
