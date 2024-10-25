#!/usr/bin/env bash
#
# Downloads and sets up the Design System components
#
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "${DIR}"/.. || exit

if [ $# -eq 0 ] || [ "$1" == "" ]; then
    echo "Usage: load-design-system-templates.sh {TAG_NAME}"
elif [ "$1" == "" ]; then
    TAG_NAME=$(curl --silent "https://api.github.com/repos/${REPO_NAME}/releases" | jq '.[0].name' | tr -d '"')
else
    TAG_NAME="$1"
fi

REPO_NAME="onsdigital/design-system"
DOWNLOAD_URL=$(curl --silent "https://api.github.com/repos/${REPO_NAME}/releases/tags/${TAG_NAME}" | jq '.assets[0].browser_download_url' | tr -d '"')
RELEASE_NAME=${DOWNLOAD_URL##*/}

echo "Fetching ${DOWNLOAD_URL}"

TEMP_DIR=$(mktemp -d)

curl --silent -L --url "https://github.com/${REPO_NAME}/releases/download/${TAG_NAME}/${RELEASE_NAME}" --output "${TEMP_DIR}/${RELEASE_NAME}"
unzip -q -o "${TEMP_DIR}/${RELEASE_NAME}" -d .
rm -rf "${TEMP_DIR}"

rm -rf ./cms/jinja2/components
rm -rf ./cms/jinja2/layout
mv -f templates/* ./cms/jinja2
rm -rf templates
echo "Saved Design System templates to 'cms/jinja2/components' and 'cms/jinja2/components'"

#
# Now load the print stylesheet
#
CDN_URL=${CDN_URL:-"https://cdn.ons.gov.uk"}
PRINT_STYLE_SHEET_FILE_PATH_PATH="cms/jinja2/assets/styles"

echo "Loading print style sheets from CDN for DS Version ${TAG_NAME}"

PRINT_STYLE_SHEET_CDN_URL="${CDN_URL}/sdc/design-system/${TAG_NAME}/css/print.css"

mkdir -p "${PRINT_STYLE_SHEET_FILE_PATH_PATH}"
TARGET_STYLE_SHEET_FILE_LOCATION="${PRINT_STYLE_SHEET_FILE_PATH_PATH}/print.css"

curl --silent --compressed "${PRINT_STYLE_SHEET_CDN_URL}" > "${TARGET_STYLE_SHEET_FILE_LOCATION}"

echo "Saved print CSS into '${TARGET_STYLE_SHEET_FILE_LOCATION}'"
