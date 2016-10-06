#!/usr/bin/env bats

load esg-setup

@test "check_prerequisites_works" {
  run check_prerequisites
  echo "${status}"
  echo "${output}"
  [ $status -eq 0 ]

}

@test "init_structure_works" {

  run init_structure
  [ $status -eq 0 ]

}

@test "check for java" {
 run which java
 [ $status -eq 0 ]

}

@test "check java version" {
 run java -version
 echo "${lines[0]}"
 [ $status -eq 0 ]
 [ "${lines[0]}" = 'java version "1.7.0_111"' ]

}
