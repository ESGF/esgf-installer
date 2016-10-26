#!/usr/bin/env bats

load esg-functions

@test "_version_cmp" {
  run _version_cmp "2:2.3.4-5", "3:2.5.3-1"
  echo "${status}"
  echo "${output}"
  [ $status -eq 0 ]

}

