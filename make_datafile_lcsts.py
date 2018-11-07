import sys
import os
import hashlib
import subprocess
import collections

import json
import tarfile
import io
import pickle as pkl
import jieba
import re


dm_single_close_quote = '\u2019' # unicode
dm_double_close_quote = '\u201d'
# acceptable ways to end a sentence
END_TOKENS = ['.', '!', '?', '...', "'", "`", '"',
              dm_single_close_quote, dm_double_close_quote, ")"]

# 暂时不需要用到
# all_train_urls = "url_lists/all_train.txt"
# all_val_urls = "url_lists/all_val.txt"
# all_test_urls = "url_lists/all_test.txt"

# lcsts_tokenized_stories_dir = "cnn_stories_tokenized"
# dm_tokenized_stories_dir = "dm_stories_tokenized"
lcsts_tokenized_stories_dir = "lcsts_stories_tokenized"
finished_files_dir = "finished_files"

#中文数据集不需要check num
# These are the number of .story files we expect there to be in cnn_stories_dir
# and dm_stories_dir
# num_expected_cnn_stories = 92579
# num_expected_dm_stories = 219506




"""分词部分由jieba.cut代替Stanford CoreNLP Tokenizer"""
# def tokenize_stories(stories_dir, tokenized_stories_dir):
#     """Maps a whole directory of .story files to a tokenized version using
#        Stanford CoreNLP Tokenizer
#     """
#     print("Preparing to tokenize {} to {}...".format(stories_dir,
#                                                      tokenized_stories_dir))
#     stories = os.listdir(stories_dir)
#     # make IO list file
#     print("Making list of files to tokenize...")
#     with open("mapping.txt", "w") as f:
#         for s in stories:
#             f.write(
#                 "{} \t {}\n".format(
#                     os.path.join(stories_dir, s),
#                     os.path.join(tokenized_stories_dir, s)
#                 )
#             )
#     command = ['java', 'edu.stanford.nlp.process.PTBTokenizer',
#                '-ioFileList', '-preserveLines', 'mapping.txt']
#     print("Tokenizing {} files in {} and saving in {}...".format(
#         len(stories), stories_dir, tokenized_stories_dir))
#     subprocess.call(command)
#     print("Stanford CoreNLP Tokenizer has finished.")
#     os.remove("mapping.txt")
#
#     # Check that the tokenized stories directory contains the same number of
#     # files as the original directory
#     num_orig = len(os.listdir(stories_dir))
#     num_tokenized = len(os.listdir(tokenized_stories_dir))
#     if num_orig != num_tokenized:
#         raise Exception(
#             "The tokenized stories directory {} contains {} files, but it "
#             "should contain the same number as {} (which has {} files). Was"
#             " there an error during tokenization?".format(
#                 tokenized_stories_dir, num_tokenized, stories_dir, num_orig)
#         )
#     print("Successfully finished tokenizing {} to {}.\n".format(
#         stories_dir, tokenized_stories_dir))

# def read_story_file(text_file):
#     with open(text_file, "r") as f:
#         # sentences are separated by 2 newlines
#         # single newlines might be image captions
#         # so will be incomplete sentence
#         lines = f.read().split('\n\n')
#     return lines
#
#
# def hashhex(s):
#     """Returns a heximal formated SHA1 hash of the input string."""
#     h = hashlib.sha1()
#     h.update(s.encode())
#     return h.hexdigest()
#
#
# def get_url_hashes(url_list):
#     return [hashhex(url) for url in url_list]
#
#
# def fix_missing_period(line):
#     """Adds a period to a line that is missing a period"""
#     if "@highlight" in line:
#         return line
#     if line == "":
#         return line
#     if line[-1] in END_TOKENS:
#         return line
#     return line + " ."
#
#
# def get_art_abs(story_file):
#     """ return as list of sentences"""
#     lines = read_story_file(story_file)
#
#     # Lowercase, truncated trailing spaces, and normalize spaces
#     # 中文不需要lower()操作
#     lines = [' '.join(line.lower().strip().split()) for line in lines]
#
#     # Put periods on the ends of lines that are missing them (this is a problem
#     # in the dataset because many image captions don't end in periods;
#     # consequently they end up in the body of the article as run-on sentences)
#     # 中文不需要这方面的操作
#     lines = [fix_missing_period(line) for line in lines]
#
#     # Separate out article and abstract sentences
#     article_lines = []
#     # highlight部分是如何处理的？作为摘要标准
#     highlights = []
#     next_is_highlight = False
#     for idx, line in enumerate(lines):
#         if line == "":
#             continue # empty line
#         elif line.startswith("@highlight"):
#             next_is_highlight = True
#         elif next_is_highlight:
#             highlights.append(line)
#         else:
#             article_lines.append(line)
#
#     return article_lines, highlights


def write_to_tar(in_file, out_file, id_offset_line, label_offset_line, abstract_offset_line, article_offset_line, offset_line, makevocab=False,scoreFilter=False, highScore = 0):
    """Reads the tokenized .story files corresponding to the urls listed in the
       url_file and writes them to a out_file.
    """

    # print("Making bin file for URLs listed in {}...".format(url_file))
    # url_list = [line.strip() for line in open(url_file)]
    # # hash值对于后续的训练到底有什么作用？
    # url_hashes = get_url_hashes(url_list)
    # story_fnames = [s+".story" for s in url_hashes]
    # num_stories = len(story_fnames)

    # 是否做词汇表，注意词汇表的格式
    if makevocab:
        vocab_counter = collections.Counter()

    i = 0;
    abstract=[]
    article = []
    id = ""
    with tarfile.open(out_file, 'w') as writer:
        with open(in_file, "r") as f:
            for line in f:
                i = i + 1;
                label = 0;
                if i % offset_line == label_offset_line and scoreFilter:
                    label = int(line.strip()[13:14])

                if not scoreFilter or label >= highScore:
                    if i % offset_line == id_offset_line:
                        # 中文数据集的id可以用数据中有的id
                        id = str(int(i / offset_line))
                    if i % offset_line == abstract_offset_line:
                        seg_list = jieba.cut(line.strip())
                        abstract.append(" ".join(seg_list))
                    if i % offset_line == article_offset_line:
                        # 以分号，句号，感叹号，问号为分隔符，处理article部分内容
                        article_line = line.strip()
                        article_list = re.split('[？。！；?;!]', article_line)
                        # 先分成句子，对于长度大于3的句子进行分词，分词后合成新的句子
                        for lice in article_list:
                            if len(lice) > 3:
                                seg_list = jieba.cut(lice)
                                article.append(" ".join(seg_list))

                        # 打开tar包，转化成json格式文件后写进tar包中
                        # Write to JSON file
                        js_example = {}
                        # id\article\abstract 部分的数据处理完成
                        # 转化成json数据格式
                        js_example['article'] = article
                        js_example['abstract'] = abstract
                        js_example['id'] = id
                        js_serialized = json.dumps(js_example, indent=4,ensure_ascii=False).encode()
                        save_file = io.BytesIO(js_serialized)
                        tar_info = tarfile.TarInfo('{}/{}.json'.format(
                            os.path.basename(out_file).replace('.tar', ''), id))
                        tar_info.size = len(js_serialized)
                        writer.addfile(tar_info, save_file)
                        #print(id)
                        # 需要把atrcile 和 abstract置空
                        article = []
                        abstract = []
                        # Write the vocab to file, if applicable
                        if makevocab:
                            art_tokens = ' '.join(article).split()
                            abs_tokens = ' '.join(abstract).split()
                            tokens = art_tokens + abs_tokens
                            tokens = [t.strip() for t in tokens] # strip
                            tokens = [t for t in tokens if t != ""] # remove empty
                            # collections里的方法
                            vocab_counter.update(tokens)

    print("Finished writing file {}\n".format(out_file))

    # write vocab to file
    if makevocab:
        print("Writing vocab file...")
        with open(os.path.join(finished_files_dir, "vocab_cnt.pkl"),
                  'wb') as vocab_file:
            pkl.dump(vocab_counter, vocab_file)
        print("Finished writing vocab file")


# def check_num_stories(stories_dir, num_expected):
#     num_stories = len(os.listdir(stories_dir))
#     if num_stories != num_expected:
#         raise Exception(
#             "stories directory {} contains {} files"
#             " but should contain {}".format(
#                 stories_dir, num_stories, num_expected)
#         )


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("USAGE: python make_datafiles.py"
              " <lcsts_stories_dir> ")
        sys.exit()
    lcsts_stories_dir = sys.argv[1]

    """中文数据集不需要check sum"""
    # Check the stories directories contain the correct number of .story files
    # check_num_stories(cnn_stories_dir, num_expected_cnn_stories)
    # check_num_stories(dm_stories_dir, num_expected_dm_stories)

    # Create some new directories
    if not os.path.exists(lcsts_tokenized_stories_dir):
        os.makedirs(lcsts_tokenized_stories_dir)
    if not os.path.exists(finished_files_dir):
        os.makedirs(finished_files_dir)

    """中文数据集直接用jieba.cut()分词"""
    # Run stanford tokenizer on both stories dirs,
    # outputting to tokenized stories directories
    # tokenize_stories(lcsts_stories_dir, lcsts_tokenized_stories_dir)
    # tokenize_stories(dm_stories_dir, dm_tokenized_stories_dir)

    # Read the tokenized stories, do a little postprocessing
    # then write to bin files
    write_to_tar(os.path.join(lcsts_stories_dir, "PART_III.txt"),os.path.join(finished_files_dir, "test.tar"), 1, 2, 4, 7, 9)
    write_to_tar(os.path.join(lcsts_stories_dir, "PART_II.txt"),os.path.join(finished_files_dir, "val.tar"), 1, 2, 4, 7, 9)
    write_to_tar(os.path.join(lcsts_stories_dir, "PART_I.txt"),os.path.join(finished_files_dir, "train.tar"), 1, 0, 3, 6, 8, makevocab=True)

