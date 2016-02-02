#!/bin/bash

FROM="jcrew_polo_tracker@$(hostname -d)"
SUBJECT="New Polos Available"
TO="$(getent aliases elliott | awk '{print $NF}')"

LOCAL_DIR=$(dirname $0)
WWW_DIR="/var/www/www.eyyit.com/jcrew"

JCREW_URL='http://www.jcrew.com/mens_category/polostees/shortsleevepolos/PRDOVR~91918/91918.jsp'
URL='http://www.eyyit.com/jcrew'

CUR_FILE='jcrew_polos_cur.png'
NEW_FILE='jcrew_polos_new.png'
OLD_FILE='jcrew_polos_old.png'

SCRAPER="${LOCAL_DIR}/jcrew_polo_tracker_scraper.js"

fping -q www.jcrew.com || exit

timeout -s KILL 5m \
  casperjs ${SCRAPER} \
    --filename="${WWW_DIR}/${NEW_FILE}" \
    --url="${JCREW_URL}" >/dev/null 2>&1 || exit

cur_sha1=$(sha1sum ${WWW_DIR}/${CUR_FILE} | cut -d ' ' -f 1)
new_sha1=$(sha1sum ${WWW_DIR}/${NEW_FILE} | cut -d ' ' -f 1)

if [[ "${new_sha1}" = "${cur_sha1}" ]]; then
  rm -f ${WWW_DIR}/${NEW_FILE}
else
  rm -f ${WWW_DIR}/${OLD_FILE}
  mv -f ${WWW_DIR}/${CUR_FILE} ${WWW_DIR}/${OLD_FILE}
  mv -f ${WWW_DIR}/${NEW_FILE} ${WWW_DIR}/${CUR_FILE}
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
      <img src="${URL}/${CUR_FILE}">
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
fi
