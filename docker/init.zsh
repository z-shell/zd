printf '%s\n' "Setting owner of /data to ${PUID}:${PGID}" >&2
sudo chown "${PUID}:${PGID}" /data
sudo chown -R "${PUID}:${PGID}" /data

# sync files between /data-static and /data
if [[ -z "$NOTHING_FANCY" ]]
then
  printf '%s\n' "Copying files from /data-static to /data" >&2
  rsync -raq /data-static/ /data
fi
