from installer.director import Director

director = Director()
director.pre_check()
director.get_cmd_line()
director.begin()
