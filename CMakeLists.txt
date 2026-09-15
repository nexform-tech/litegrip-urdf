cmake_minimum_required(VERSION 3.10)
project(litegrip_urdf)

find_package(ament_cmake REQUIRED)

# 纯描述包：只需把资源目录安装到 share/<pkg>/
install(
  DIRECTORY urdf launch config meshes
  DESTINATION share/${PROJECT_NAME}
)

# 可选：若客户环境装有 ament_lint_auto，则启用包规范检查
find_package(ament_lint_auto QUIET)
if(ament_lint_auto_FOUND)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
