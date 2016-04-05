#!/bin/bash

/bin/ps -p $(cat /var/run/jcrew_polo_tracker.pid 2>/dev/null) >/dev/null 2>&1 && exit
echo $$ > /var/run/jcrew_polo_tracker.pid

FROM="jcrew_polo_tracker@$(hostname -d)"
SUBJECT="New Polos Available"
TO="$(getent aliases elliott | awk '{print $NF}')"

LOCAL_DIR=$(dirname $0)
JCREW_URL='http://www.jcrew.com/mens_category/polostees/shortsleevepolos/PRDOVR~91918/91918.jsp'
NEW_FILE="jcrew_polos_$(/bin/date +%Y-%m-%d_%H:%M).png"
OLD_FILE="$(/usr/bin/basename $(/bin/ls -1t ${WWW_DIR}/*.png | /usr/bin/head -n 1))"
SCRAPER="${LOCAL_DIR}/scraper.js"
URL='https://www.eyyit.com/jcrew'
WWW_DIR="/var/www/www.eyyit.com/jcrew"

/usr/bin/find ${WWW_DIR} -type f -name '*.png' -mtime 14 -exec rm -f {} \;

fping -q www.jcrew.com || exit

timeout -s KILL 5m \
  casperjs ${SCRAPER} \
    --filename="${WWW_DIR}/${NEW_FILE}" \
    --url="${JCREW_URL}" >/dev/null 2>&1 || exit

new_sha1=$(sha1sum ${WWW_DIR}/${NEW_FILE} | cut -d ' ' -f 1)
old_sha1=$(sha1sum ${WWW_DIR}/${OLD_FILE} | cut -d ' ' -f 1)

if [[ "${new_sha1}" = "${cur_sha1}" ]]; then
  rm -f ${WWW_DIR}/${NEW_FILE}
  exit 0
fi
(cat << EOF
--001a11c133c8af0b9a04e750283e
Content-Type: text/plain; charset=ISO-8859-1

${JCREW_URL}

--001a11c133c8af0b9a04e750283e
Content-Type: text/html; charset=ISO-8859-1

  <a href="${JCREW_URL}">${JCREW_URL}</a>
  <br>
  <br>
  <b>New:</b>
  <blockquote style="margin:0 0 0 40px;border:none;padding:0px">
    <a href="${JCREW_URL}">
      <img src="${URL}/${NEW_FILE}">
    </a>
  </blockquote>
  <br><br>
  <b>Old:</b>
  <blockquote style="margin:0 0 0 40px;border:none;padding:0px">
    <a href="${JCREW_URL}">
      <img src="${URL}/${OLD_FILE}">
    </a>
  </blockquote>

--001a11c133c8af0b9a04e750283e--
EOF
) | bsd-mailx \
  -a "From: ${FROM}" \
  -a 'MIME-Version: 1.0' \
  -a 'Content-Type: multipart/alternative; boundary=001a11c133c8af0b9a04e750283e' \
  -s "${SUBJECT}" \
  "${TO}"
/bin/rm -f /var/run/jcrew_polo_tracker.pid
