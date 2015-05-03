#!/bin/bash

FROM="jcrew_polo_tracker@$(hostname -d)"
SUBJECT="New Polos Available"
TO="$(getent aliases elliott | awk '{print $NF}')"

LOCAL_DIR=$(dirname $0)
WWW_DIR="/var/www/www.eyyit.com/www/jcrew"

JCREW_URL='http://www.jcrew.com/mens_category/polostees/shortsleevepolos/PRDOVR~91918/91918.jsp'
URL='http://www.eyyit.com/jcrew'

OLD_PREFIX='jcrew_polos_old'
CUR_PREFIX='jcrew_polos_cur'

SCRAPER="${LOCAL_DIR}/jcrew_polo_tracker_scraper.js"
NEW_FILE="${WWW_DIR}/jcrew_polos.png"
OLD_FILE=$(find ${WWW_DIR} -type f -name "${OLD_PREFIX}*.png" | grep 'png' || \
  (touch ${WWW_DIR}/${OLD_PREFIX}.0.png && echo ${WWW_DIR}/${OLD_PREFIX}.0.png))
CUR_FILE=$(find ${WWW_DIR} -type f -name "${CUR_PREFIX}*.png" | grep 'png' || \
  (touch ${WWW_DIR}/${CUR_PREFIX}.0.png && echo ${WWW_DIR}/${CUR_PREFIX}.0.png))

timeout -s KILL 5m \
  casperjs ${SCRAPER} \
    --filename="${NEW_FILE}" \
    --url="${JCREW_URL}" || exit

new_sha1=$(sha1sum ${NEW_FILE} | cut -d ' ' -f 1)
cur_sha1=$(basename ${CUR_FILE} | cut -d '.' -f 3)

if [[ "${new_sha1}" == "${cur_sha1}" ]]; then
  rm -f ${NEW_FILE}
else
  rm -f ${OLD_FILE}
  mv -f ${CUR_FILE} ${WWW_DIR}/${OLD_PREFIX}.${cur_sha1}.png
  mv -f ${NEW_FILE} ${WWW_DIR}/${CUR_PREFIX}.${new_sha1}.png
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
      <img src="${URL}/${CUR_PREFIX}.${new_sha1}.png">
    </a>
  </blockquote>
  <br><br>
  <b>Old:</b>
  <blockquote style="margin:0 0 0 40px;border:none;padding:0px">
    <a href="${JCREW_URL}">
      <img src="${URL}/${OLD_PREFIX}.${cur_sha1}.png">
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
