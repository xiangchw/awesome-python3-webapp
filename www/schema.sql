drop database if exists awesome;
create database awesome;
use awesome;

#   给本机用户www-data授权select,insert,update和delete该awesome数据库中所有表.
#   密码www-data
grant select, insert, update, delete on awesome.* to 'www-data'@'localhost' identified by 'www-data';

create table users
(
    `id`         varchar(50)  not null,
    `email`      varchar(50)  not null,
    `passwd`     varchar(50)  not null,
    `admin`      bool         not null,
    `name`       varchar(50)  not null,
    `image`      varchar(500) not null,
    `created_at` real         not null, #   如果mysql开启REAL_AS_FLOAT选项,REAL当做FLOAT,否则当做DOUBLE处理
    unique key `idx_email` (`email`),   #    唯一索引, 邮件地址
    key `idx_create_at` (`created_at`), #   普通索引,创建时间
    primary key (`id`)
) engine = innodb
  default charset utf8;

create table blogs
(
    `id`         varchar(50)  not null,
    `user_id`    varchar(50)  not null,
    `user_name`  varchar(50)  not null,
    `user_image` varchar(500) not null,
    `name`       varchar(50)  not null,
    `summary`    varchar(200) not null,
    `content`    mediumtext   not null,
    `created_at` real         not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine = innodb
  default charset = utf8;

create table comments
(
    `id`         varchar(50)  not null,
    `blog_id`    varchar(50)  not null,
    `user_id`    varchar(50)  not null,
    `user_name`  varchar(50)  not null,
    `user_image` varchar(500) not null,
    `content`    mediumtext   not null,
    `created_at` real         not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine = innodb
  default charset = utf8;